"""
Backend de execução via subprocesso local.

Executa o código em um processo filho do próprio interpretador do
servidor, com ambiente restrito (whitelist) e saídas limitadas.
Rápido e sem dependências externas; indicado para desenvolvimento e
ambientes de confiança única.
"""

import asyncio
import os
import site
import sys
from pathlib import Path

from pyflow.core.backends.base import ExecutionBackend, RawExecution
from pyflow.core.backends._util import _execute_process

# Fixed script name inside the per-request work dir. Keeps the
# pyflow_tmp_*.py pattern so route-level sanitize_path also matches.
USER_CODE_FILENAME = "pyflow_tmp_user_code.py"


def _build_child_env() -> dict:
    """Build a minimal env for the child process.

    A whitelist prevents user code from reading server secrets
    (API keys, tokens) and keeps the execution environment clean.

    PYTHONUSERBASE is forwarded when the server interpreter has a user
    site, so the child sees the same user-installed packages (e.g.
    matplotlib) as the parent. It only exposes an import path, never an
    environment secret.
    """
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    }
    user_base = os.environ.get("PYTHONUSERBASE") or site.USER_BASE
    if user_base and os.path.isdir(user_base):
        env["PYTHONUSERBASE"] = user_base
    return env


class SubprocessBackend(ExecutionBackend):
    """Executes Python code in an isolated local subprocess."""

    async def run(
        self,
        code: str,
        stdin=None,
        timeout_seconds: int = 30,
        max_output_chars: int = 100_000,
        cwd: str = "",
        on_output=None,
    ) -> RawExecution:
        tmp_file = Path(cwd) / USER_CODE_FILENAME
        tmp_file.write_text(code, encoding="utf-8")

        # Use -u for unbuffered output to catch prints immediately.
        # Use sys.executable to ensure we use the same python interpreter.
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-u", str(tmp_file),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,  # Run in the work dir to avoid polluting project dir
            env=_build_child_env(),
        )
        return await _execute_process(
            process,
            stdin,
            timeout_seconds,
            max_output_chars,
            on_output,
        )
