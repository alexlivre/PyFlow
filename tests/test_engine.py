"""Engine tests: environment isolation and execution controls."""

import asyncio

from pyflow.core.engine import _build_child_env, execute_code


def test_build_child_env_whitelists_variables(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-should-not-leak")
    env = _build_child_env()
    assert "OPENAI_API_KEY" not in env
    assert "PYTHONIOENCODING" in env
    assert "PYTHONUNBUFFERED" in env


def test_executed_code_cannot_read_server_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-should-not-leak")
    result = asyncio.run(
        execute_code(
            request_id="req_env_test",
            code="import os; print(os.environ.get('OPENAI_API_KEY'))",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert result.status == "success"
    assert "sk-secret-should-not-leak" not in result.stdout
