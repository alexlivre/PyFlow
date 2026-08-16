"""Engine tests: environment isolation and execution controls."""

import asyncio
import base64

import pytest

from pyflow.core.engine import _build_child_env, execute_code
from pyflow.core.runner_tpl import RUNNER_TEMPLATE


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


def test_success_branch_does_not_leak_temp_path():
    result = asyncio.run(
        execute_code(
            request_id="req_success_leak",
            code="print(__file__)",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert result.status == "success"
    assert "<user_code>" in result.stdout
    assert "pyflow_tmp" not in result.stdout


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


def test_truncated_traceback_does_not_leak_temp_path():
    result = asyncio.run(
        execute_code(
            request_id="req_trunc_leak",
            code="raise Exception('x' * 100000)",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert result.output_truncated is True
    assert "<user_code>" in result.stderr
    assert "pyflow_tmp" not in result.stderr


def test_error_message_does_not_leak_temp_path():
    result = asyncio.run(
        execute_code(
            request_id="req_msg_leak",
            code="raise Exception(__file__)",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert result.status == "error"
    assert result.diagnostics is not None
    assert "pyflow_tmp" not in result.diagnostics.message
    assert "<user_code>" in result.diagnostics.message


def test_without_rich_output_images_empty():
    result = asyncio.run(
        execute_code(
            request_id="req_plain_rich",
            code="print('hello')",
            stdin=None,
            timeout_seconds=5,
            max_output_chars=1000,
        )
    )
    assert result.status == "success"
    assert result.images == []


def test_rich_output_collects_matplotlib_figure_as_png():
    pytest.importorskip("matplotlib")
    result = asyncio.run(
        execute_code(
            request_id="req_rich_fig",
            code="import matplotlib.pyplot as plt\nplt.plot([1, 2, 3])\nplt.show()\n",
            stdin=None,
            timeout_seconds=30,
            max_output_chars=100000,
            rich_output=True,
        )
    )
    assert result.status == "success"
    assert len(result.images) == 1
    assert base64.b64decode(result.images[0])[:4] == b"\x89PNG"
    assert "PYFLOW_IMAGES" not in result.stdout


def test_rich_output_collects_multiple_figures():
    pytest.importorskip("matplotlib")
    result = asyncio.run(
        execute_code(
            request_id="req_rich_figs2",
            code=(
                "import matplotlib.pyplot as plt\n"
                "plt.figure(1)\n"
                "plt.plot([1, 2, 3])\n"
                "plt.figure(2)\n"
                "plt.plot([3, 2, 1])\n"
            ),
            stdin=None,
            timeout_seconds=30,
            max_output_chars=100000,
            rich_output=True,
        )
    )
    assert result.status == "success"
    assert len(result.images) == 2
    assert all(base64.b64decode(img)[:4] == b"\x89PNG" for img in result.images)
    assert "PYFLOW_IMAGES" not in result.stdout


def test_rich_output_keeps_user_stdout_and_strips_marker():
    pytest.importorskip("matplotlib")
    result = asyncio.run(
        execute_code(
            request_id="req_rich_print",
            code="import matplotlib.pyplot as plt\nprint('hello')\nplt.plot([1, 2, 3])\n",
            stdin=None,
            timeout_seconds=30,
            max_output_chars=100000,
            rich_output=True,
        )
    )
    assert result.status == "success"
    assert "hello" in result.stdout
    assert "PYFLOW_IMAGES" not in result.stdout
    assert len(result.images) == 1


def test_rich_output_without_figures_has_no_images():
    pytest.importorskip("matplotlib")
    result = asyncio.run(
        execute_code(
            request_id="req_rich_nofig",
            code="print('no figures here')",
            stdin=None,
            timeout_seconds=30,
            max_output_chars=100000,
            rich_output=True,
        )
    )
    assert result.status == "success"
    assert result.images == []
    assert "PYFLOW_IMAGES" not in result.stdout


def test_rich_output_degrades_when_matplotlib_unavailable(monkeypatch):
    broken_template = RUNNER_TEMPLATE.replace(
        'import matplotlib\nmatplotlib.use("Agg")\nimport matplotlib.pyplot as plt',
        "import _nonexistent_module_xyz",
    )
    monkeypatch.setattr("pyflow.core.runner_tpl.RUNNER_TEMPLATE", broken_template)
    result = asyncio.run(
        execute_code(
            request_id="req_rich_nompl",
            code="print('sem matplotlib')",
            stdin=None,
            timeout_seconds=10,
            max_output_chars=1000,
            rich_output=True,
        )
    )
    assert result.status == "success"
    assert "sem matplotlib" in result.stdout
    assert result.images == []
    assert "PYFLOW_IMAGES" not in result.stdout


def test_truncation_branch_extracts_images(monkeypatch):
    monkeypatch.setattr(
        "pyflow.core.engine._extract_images",
        lambda stdout: ("stripped", ["fake"]),
    )
    result = asyncio.run(
        execute_code(
            request_id="req_trunc_rich",
            code="print('x' * 5000)",
            stdin=None,
            timeout_seconds=10,
            max_output_chars=1,
            rich_output=True,
        )
    )
    assert result.output_truncated is True
    assert result.images == ["fake"]
    assert "stripped" in result.stdout
    assert "PYFLOW_IMAGES" not in result.stdout


def test_truncation_does_not_leak_partial_images_marker():
    pytest.importorskip("matplotlib")
    result = asyncio.run(
        execute_code(
            request_id="req_trunc_marker",
            code="import matplotlib.pyplot as plt\nplt.plot([1, 2, 3])\n",
            stdin=None,
            timeout_seconds=30,
            max_output_chars=40,
            rich_output=True,
        )
    )
    assert result.output_truncated is True
    assert result.images == []
    assert "PYFLOW_IMAGES" not in result.stdout
