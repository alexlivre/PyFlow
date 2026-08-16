"""
Backend de execução via sandbox Docker.

Executa o código dentro de um container efêmero e fortemente restrito
(sem rede, memória e processos limitados, filesystem read-only, sem
capabilities, sem novos privilégios, usuário nobody). Indicado para
produção e ambientes multi-usuário, onde o isolamento do host importa.

O código é enviado via stdin (`python -u -`), evitando montar volumes.

Limitação v1: este backend suporta apenas `stdin=None`. Quando o código
do usuário usa `input()`, o campo `stdin` é necessário; o backend então
levanta NotImplementedError em vez de degradar silenciosamente para o
subprocesso local (que quebraria o isolamento prometido). Use
PYFLOW_EXECUTION_BACKEND=subprocess para código interativo.

Nota: o docker daemon deve estar em execução; o client docker (CLI) é
morto em timeout, e em plataformas onde matar o CLI não encerra o
container, o container pode permanecer até ser removido manualmente
(com `--rm` ele é removido ao finalizar).
"""

import asyncio
from typing import List

from pyflow.core.backends.base import ExecutionBackend, RawExecution
from pyflow.core.backends._util import _execute_process
from pyflow.core.config import settings


def _build_docker_command(image: str) -> List[str]:
    """Build the `docker run` command for the sandboxed execution."""
    return [
        "docker",
        "run",
        "--rm",
        "--network", "none",
        "--memory", "128m",
        "--pids-limit", "32",
        "--read-only",
        "--tmpfs", "/tmp",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", "nobody",
        "-i",
        "-e", "PYTHONIOENCODING=utf-8",
        image,
        "python", "-u", "-",
    ]


class DockerBackend(ExecutionBackend):
    """Executes Python code inside a hardened ephemeral container."""

    async def run(
        self,
        code: str,
        stdin=None,
        timeout_seconds: int = 30,
        max_output_chars: int = 100_000,
        cwd: str = "",
        on_output=None,
    ) -> RawExecution:
        if stdin is not None:
            raise NotImplementedError(
                "The docker backend does not support stdin in v1; "
                "use PYFLOW_EXECUTION_BACKEND=subprocess for interactive input."
            )

        process = await asyncio.create_subprocess_exec(
            *_build_docker_command(settings.PYFLOW_DOCKER_IMAGE),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        # The code itself travels via stdin (`python -u -`), so the user
        # stdin channel is not available (see the v1 limitation above).
        return await _execute_process(
            process,
            code,
            timeout_seconds,
            max_output_chars,
            on_output,
        )
