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


def test_output_limit_returns_output_limit_status():
    result = asyncio.run(
        execute_code(
            request_id="req_trunc",
            code="print('x' * 5000)",
            stdin=None,
            timeout_seconds=10,
            max_output_chars=100,
        )
    )
    assert result.status == "error"
    assert result.output_truncated is True
    assert result.diagnostics.error_type == "OutputLimitExceeded"


def test_timeout_kills_process():
    result = asyncio.run(
        execute_code(
            request_id="req_timeout",
            code="import time; time.sleep(5)",
            stdin=None,
            timeout_seconds=1,
            max_output_chars=1000,
        )
    )
    assert result.status == "timeout"
    assert result.diagnostics.error_type == "Timeout"


def test_output_limit_with_blocked_process_returns_truncation_status():
    result = asyncio.run(
        execute_code(
            request_id="req_trunc_blocked",
            code="for _ in range(100000): print('x' * 100)",
            stdin=None,
            timeout_seconds=2,
            max_output_chars=100,
        )
    )
    assert result.status == "error"
    assert result.output_truncated is True
    assert result.diagnostics.error_type == "OutputLimitExceeded"


def test_stdin_is_delivered_to_input():
    result = asyncio.run(
        execute_code(
            request_id="req_stdin",
            code="name = input('Nome: '); print(f'Olá {name}')",
            stdin="Maria\n",
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert result.status == "success"
    assert "Olá Maria" in result.stdout


def test_blocked_when_input_without_stdin():
    result = asyncio.run(
        execute_code(
            request_id="req_blocked",
            code="input()",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert result.status == "blocked"
    assert result.diagnostics.error_type == "InputRequiresStdin"


def test_syntax_error_diagnostics():
    result = asyncio.run(
        execute_code(
            request_id="req_syntax",
            code="if True\n",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert result.status == "error"
    assert result.diagnostics.error_type == "SyntaxError"
    assert result.diagnostics.line is not None


def test_traceback_paths_are_sanitized():
    result = asyncio.run(
        execute_code(
            request_id="req_sanitize",
            code="x = 1/0",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert "<user_code>" in result.stderr
    assert "pyflow_tmp" not in result.stderr
