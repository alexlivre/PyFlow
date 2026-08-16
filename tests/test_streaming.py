"""Streaming tests: NDJSON endpoint, engine emit callback, and _read_stream on_chunk."""

import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient

from pyflow.main import app
from pyflow.core.engine import _read_stream, execute_code_stream
from pyflow.core.security import get_or_create_token

HEADERS = {"X-PyFlow-Token": get_or_create_token()}


class FakeStreamReader:
    """Minimal stand-in for asyncio.StreamReader with a fixed chunk sequence."""

    def __init__(self, chunks):
        self._chunks = list(chunks)

    async def read(self, n):
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


def test_read_stream_calls_on_chunk_in_order():
    received = []
    stream = FakeStreamReader([b"abc", b"def", b"ghi"])
    output, truncated = asyncio.run(
        _read_stream(stream, limit=1000, on_chunk=received.append)
    )
    assert output == "abcdefghi"
    assert truncated is False
    assert received == ["abc", "def", "ghi"]


def test_read_stream_on_chunk_fires_before_limit_check():
    received = []
    stream = FakeStreamReader([b"x" * 100, b"y" * 100])
    output, truncated = asyncio.run(
        _read_stream(stream, limit=150, on_chunk=received.append)
    )
    assert truncated is True
    assert output == "x" * 100 + "y" * 50
    assert received == ["x" * 100, "y" * 100]


def test_read_stream_without_on_chunk_still_reads():
    stream = FakeStreamReader([b"abc", b"def"])
    output, truncated = asyncio.run(_read_stream(stream, limit=1000))
    assert output == "abcdef"
    assert truncated is False


def test_execute_code_stream_emits_chunks():
    chunks = []

    async def collect(stream, data):
        chunks.append((stream, data))

    result = asyncio.run(
        execute_code_stream(
            request_id="req_stream_engine",
            code="import time\nfor i in range(3):\n    print(i)\n    time.sleep(0.05)\n",
            stdin=None,
            timeout_seconds=10,
            max_output_chars=1000,
            emit=collect,
        )
    )
    assert result.status == "success"
    stdout_events = [data for stream, data in chunks if stream == "stdout"]
    assert "".join(stdout_events) == result.stdout
    for digit in ("0", "1", "2"):
        assert digit in result.stdout


@pytest.mark.asyncio
async def test_run_stream_emits_output_before_done():
    code = "import time\nfor i in range(3):\n    print(i)\n    time.sleep(0.1)\n"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", timeout=30
    ) as client:
        async with client.stream(
            "POST",
            "/run/stream",
            json={"code": code, "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        ) as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("application/x-ndjson")
            events = []
            async for line in resp.aiter_lines():
                if line.strip():
                    events.append(json.loads(line))

    types = [event["type"] for event in events]
    assert types[-1] == "done"
    first_done = next(i for i, t in enumerate(types) if t == "done")
    assert any(t == "output" for t in types[:first_done])

    result = events[-1]["result"]
    assert result["status"] == "success"
    for digit in ("0", "1", "2"):
        assert digit in result["stdout"]


@pytest.mark.asyncio
async def test_run_stream_timeout_emits_done_not_error():
    code = "import time; time.sleep(5)"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", timeout=30
    ) as client:
        async with client.stream(
            "POST",
            "/run/stream",
            json={"code": code, "timeout_seconds": 1, "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        ) as resp:
            assert resp.status_code == 200
            events = []
            async for line in resp.aiter_lines():
                if line.strip():
                    events.append(json.loads(line))

    types = [event["type"] for event in events]
    assert "done" in types
    assert "error" not in types
    done = [event for event in events if event["type"] == "done"][-1]
    assert done["result"]["diagnostics"]["error_type"] == "Timeout"


@pytest.mark.asyncio
async def test_run_stream_output_limit_truncation():
    code = "print('x' * 5000)"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", timeout=30
    ) as client:
        async with client.stream(
            "POST",
            "/run/stream",
            json={"code": code, "max_output_chars": 100, "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        ) as resp:
            assert resp.status_code == 200
            events = []
            async for line in resp.aiter_lines():
                if line.strip():
                    events.append(json.loads(line))

    result = events[-1]["result"]
    assert result["output_truncated"] is True
    assert result["diagnostics"]["error_type"] == "OutputLimitExceeded"


@pytest.mark.asyncio
async def test_run_stream_requires_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/run/stream",
            json={"code": "print(1)"},
            headers={"Host": "localhost"},
        )
    assert resp.status_code == 401
