"""Backend tests: subprocess smoke, docker command construction, and engine wiring."""

import asyncio

import pytest

from pyflow.core.backends import ExecutionBackend, RawExecution, get_backend
from pyflow.core.backends.docker_backend import DockerBackend
from pyflow.core.backends.subprocess_backend import SubprocessBackend
from pyflow.core.config import settings
from pyflow.core.engine import execute_code


class FakeStreamReader:
    """Minimal stand-in for asyncio.StreamReader with a fixed chunk sequence."""

    def __init__(self, chunks=()):
        self._chunks = list(chunks)

    async def read(self, n):
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class FakePipe:
    def __init__(self):
        self.data = b""

    def write(self, data):
        self.data += data

    def close(self):
        pass

    async def drain(self):
        pass


class FakeProcess:
    """Minimal stand-in for asyncio.subprocess.Process (no real pipes)."""

    def __init__(self, returncode=0):
        self.stdin = FakePipe()
        self.stdout = FakeStreamReader()
        self.stderr = FakeStreamReader()
        self.returncode = returncode
        self.pid = 12345

    async def wait(self):
        return self.returncode


def test_subprocess_backend_run_returns_raw_execution(tmp_path):
    result = asyncio.run(
        SubprocessBackend().run(
            code="print('hello from backend')",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
            cwd=str(tmp_path),
        )
    )
    assert isinstance(result, RawExecution)
    assert result.stdout.strip() == "hello from backend"
    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.output_truncated is False


def test_docker_backend_builds_sandboxed_command(monkeypatch, tmp_path):
    received = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        received["args"] = args
        return FakeProcess()

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

    result = asyncio.run(
        DockerBackend().run(
            code="print('hi')",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
            cwd=str(tmp_path),
        )
    )
    assert list(received["args"]) == [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--memory",
        "128m",
        "--pids-limit",
        "32",
        "--read-only",
        "--tmpfs",
        "/tmp",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        "nobody",
        "-i",
        "-e",
        "PYTHONIOENCODING=utf-8",
        "python:3.11.9-slim",
        "python",
        "-u",
        "-",
    ]
    assert result.exit_code == 0


def test_docker_backend_rejects_stdin(tmp_path):
    with pytest.raises(NotImplementedError):
        asyncio.run(
            DockerBackend().run(
                code="input()",
                stdin="Maria\n",
                timeout_seconds=5,
                max_output_chars=1000,
                cwd=str(tmp_path),
            )
        )


def test_get_backend_defaults_to_subprocess():
    assert isinstance(get_backend(), SubprocessBackend)


def test_get_backend_switches_to_docker(monkeypatch):
    monkeypatch.setattr("pyflow.core.backends._backend_cache", {})
    monkeypatch.setattr(settings, "PYFLOW_EXECUTION_BACKEND", "docker")
    assert isinstance(get_backend(), DockerBackend)


def test_engine_runs_code_through_configured_backend(monkeypatch):
    class FakeBackend(ExecutionBackend):
        def __init__(self):
            self.code = None

        async def run(
            self, code, stdin, timeout_seconds, max_output_chars, cwd, on_output=None
        ):
            self.code = code
            return RawExecution(stdout="fake stdout", stderr="", exit_code=0, timed_out=False)

    fake = FakeBackend()
    monkeypatch.setattr("pyflow.core.engine.get_backend", lambda: fake)

    result = asyncio.run(
        execute_code(
            request_id="req_fake_backend",
            code="print(1)",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert result.status == "success"
    assert result.stdout == "fake stdout"
    assert fake.code == "print(1)"


def test_engine_maps_backend_timeout_to_timeout_status(monkeypatch):
    class TimeoutBackend(ExecutionBackend):
        async def run(
            self, code, stdin, timeout_seconds, max_output_chars, cwd, on_output=None
        ):
            return RawExecution(stdout="", stderr="", exit_code=None, timed_out=True)

    monkeypatch.setattr("pyflow.core.engine.get_backend", lambda: TimeoutBackend())

    result = asyncio.run(
        execute_code(
            request_id="req_fake_timeout",
            code="import time; time.sleep(5)",
            stdin=None,
            timeout_seconds=1,
            max_output_chars=1000,
        )
    )
    assert result.status == "timeout"
    assert result.diagnostics.error_type == "Timeout"
