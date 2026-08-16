"""API integration tests via ASGI transport (no real server needed)."""

import asyncio
import time

import pytest
from httpx import ASGITransport, AsyncClient

from pyflow.main import app
from pyflow.api import routes_run, routes_stream
from pyflow.core.concurrency import AsyncSemaphore
from pyflow.core.security import get_or_create_token

HEADERS = {"X-PyFlow-Token": get_or_create_token()}


@pytest.fixture
def single_run_slot(monkeypatch):
    """Replace the shared run semaphore with one that allows a single slot."""
    sem = AsyncSemaphore(1)
    monkeypatch.setattr(routes_run, "_run_semaphore", sem)
    monkeypatch.setattr(routes_stream, "_run_semaphore", sem)
    return sem


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health", headers={"Host": "localhost"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_run_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/run",
            json={"code": "print(2+2)", "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "4" in body["stdout"]
    assert body["request_id"].startswith("req_")


@pytest.mark.asyncio
async def test_run_error_with_diagnostics():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/run",
            json={"code": "x = 1/0", "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        )
    body = resp.json()
    assert body["status"] == "error"
    assert body["diagnostics"]["error_type"] == "ZeroDivisionError"
    assert body["diagnostics"]["line"] == 1


@pytest.mark.asyncio
async def test_chat_requires_ai_config():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/chat",
            json={"user_message": "oi"},
            headers={**HEADERS, "Host": "localhost"},
        )
    assert resp.status_code == 200
    assert "Nenhuma configuração" in resp.json()["reply"]


@pytest.mark.asyncio
async def test_code_too_large():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/run",
            json={"code": "#" * 200_000, "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        )
    body = resp.json()
    assert body["status"] == "error"
    assert body["diagnostics"]["error_type"] == "CodeTooLarge"


@pytest.mark.asyncio
async def test_run_rejects_second_concurrent_execution(single_run_slot):
    sem = single_run_slot
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = asyncio.create_task(
            client.post(
                "/run",
                json={"code": "import time; time.sleep(1)", "ai_explain_on_error": False},
                headers={**HEADERS, "Host": "localhost"},
            )
        )
        for _ in range(100):
            if sem.locked():
                break
            await asyncio.sleep(0.01)
        assert sem.locked()
        second = await client.post(
            "/run",
            json={"code": "print(1)", "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        )
        first_resp = await first
        after = await client.post(
            "/run",
            json={"code": "print(2)", "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        )
    assert first_resp.status_code == 200
    assert first_resp.json()["status"] == "success"
    assert second.status_code == 429
    assert second.headers["Retry-After"] == "1"
    assert "Too many concurrent executions" in second.json()["detail"]
    assert after.status_code == 200


@pytest.mark.asyncio
async def test_run_second_request_returns_429_without_hang(single_run_slot):
    """Burst-hang regression: an extra request must get 429 promptly, not queue."""
    sem = single_run_slot
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = asyncio.create_task(
            client.post(
                "/run",
                json={"code": "import time; time.sleep(1)", "ai_explain_on_error": False},
                headers={**HEADERS, "Host": "localhost"},
            )
        )
        for _ in range(100):
            if sem.locked():
                break
            await asyncio.sleep(0.01)
        assert sem.locked()
        start = time.monotonic()
        second = await client.post(
            "/run",
            json={"code": "print(1)", "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        )
        elapsed = time.monotonic() - start
        await first
    assert second.status_code == 429
    assert elapsed < 0.5


@pytest.mark.asyncio
async def test_run_stream_rejects_second_concurrent_execution(single_run_slot):
    sem = single_run_slot
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", timeout=30
    ) as client:

        async def hold_stream():
            async with client.stream(
                "POST",
                "/run/stream",
                json={"code": "import time; time.sleep(1)", "ai_explain_on_error": False},
                headers={**HEADERS, "Host": "localhost"},
            ) as resp:
                assert resp.status_code == 200
                return await resp.aread()

        first = asyncio.create_task(hold_stream())
        for _ in range(100):
            if sem.locked():
                break
            await asyncio.sleep(0.01)
        assert sem.locked()
        second = await client.post(
            "/run/stream",
            json={"code": "print(1)", "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        )
        await first
        after = await client.post(
            "/run/stream",
            json={"code": "print(2)", "ai_explain_on_error": False},
            headers={**HEADERS, "Host": "localhost"},
        )
    assert second.status_code == 429
    assert second.headers["Retry-After"] == "1"
    assert "Too many concurrent executions" in second.json()["detail"]
    assert after.status_code == 200
