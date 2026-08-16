"""
Motor de execução de código Python do PyFlow.

Este módulo é responsável pela execução segura de código Python em
subprocessos isolados, com controle de timeout, limites de saída
e captura de streams stdout/stderr.

Funcionalidades principais:
    - Execução assíncrona de código Python
    - Timeout configurável com terminação forçada
    - Limite de caracteres na saída
    - Captura de stdin para programas interativos
    - Diagnósticos estruturados de erros
    - Limpeza automática de arquivos temporários

A execução ocorre em um arquivo temporário para isolar o código
do usuário do ambiente do servidor.
"""

import asyncio
import json
import shutil
import time
from pathlib import Path
from tempfile import gettempdir
from typing import Awaitable, Callable, List, Optional, Tuple
from loguru import logger

from pyflow.core.models import RunResponse, Diagnostics
from pyflow.core.diagnostics import (
    parse_traceback_str,
    create_blocked_diagnostics,
    create_timeout_diagnostics,
    create_output_limit_diagnostics,
)
from pyflow.core.runner_tpl import IMAGES_MARKER_PREFIX, build_rich_script
from pyflow.core.backends import get_backend
from pyflow.core.backends._util import _read_stream, _sanitize_output
from pyflow.core.backends.subprocess_backend import _build_child_env, USER_CODE_FILENAME


def _extract_images(stdout: str) -> Tuple[str, List[str]]:
    """Pull PYFLOW_IMAGES marker lines out of stdout.

    Returns the stdout without marker lines and the base64 PNGs listed in
    the last valid marker. Incomplete markers (e.g. cut mid-payload by
    output truncation) are stripped from the output too, but yield no
    images. Missing markers leave the output untouched and produce an
    empty list.
    """
    images = []
    kept_lines = []
    for line in stdout.splitlines():
        if not line.startswith(IMAGES_MARKER_PREFIX):
            kept_lines.append(line)
            continue
        try:
            payload = json.loads(line[len(IMAGES_MARKER_PREFIX):])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list) and all(isinstance(img, str) for img in payload):
            images = payload
    return "\n".join(kept_lines), images


async def _noop_emit(stream: str, data: str) -> None:
    """Default emit callback that discards streamed chunks."""
    return None


async def execute_code_stream(
    request_id: str,
    code: str,
    stdin: Optional[str],
    timeout_seconds: int,
    max_output_chars: int,
    emit: Optional[Callable[[str, str], Awaitable[None]]] = None,
    include_raw_traceback: bool = False,
    rich_output: bool = False
) -> RunResponse:
    """
    Executa código Python através do backend de execução configurado
    (subprocesso local por padrão, ou sandbox Docker).

    Cria um arquivo temporário com o código, executa em um subprocesso
    com timeout e limites de saída, captura stdout/stderr e retorna
    um resultado estruturado.

    Args:
        request_id: Identificador único da requisição.
        code: Código Python a ser executado.
        stdin: Entrada padrão para o código (opcional).
        timeout_seconds: Tempo máximo de execução em segundos.
        max_output_chars: Limite máximo de caracteres na saída.
        emit: Callback assíncrono chamado com (nome do stream, chunk) para
            cada chunk bruto lido de stdout/stderr.
        include_raw_traceback: Se o traceback completo (não sanitizado)
            deve ser incluído no diagnóstico.
        rich_output: Se True, executa o código dentro do runner wrapper,
            coletando figuras matplotlib abertas como imagens base64.

    Returns:
        RunResponse: Resultado da execução com status, saídas e diagnósticos.

    Note:
        - Se o código contém input() e stdin não foi fornecido,
          retorna status 'blocked'.
        - Se o timeout é excedido, o processo é terminado forçadamente.
        - Se o limite de saída é excedido, a saída é truncada.
        - Arquivos temporários são limpos automaticamente.
    """
    
    start_time = time.time()
    
    # 1. Validation (Input)
    if "input(" in code and stdin is None:
        return RunResponse(
            status="blocked",
            stdout="",
            stderr="Execução bloqueada: seu código usa input(). Envie o campo 'stdin'.",
            exit_code=None,
            execution_time_ms=0,
            output_truncated=False,
            diagnostics=create_blocked_diagnostics("O código contém input() mas nenhum stdin foi fornecido."),
            request_id=request_id
        )

    # Rich output wraps the user code at module level (indent-sensitive);
    # the wrapped script runs in the same isolated subprocess.
    script = build_rich_script(code) if rich_output else code

    # 2. Stream Bridge
    # Chunks are pushed into a queue by the (sync) reader callbacks and
    # drained by an async task that awaits the emit callback.
    emit = emit or _noop_emit
    chunk_queue = asyncio.Queue()

    async def emit_loop() -> None:
        while True:
            item = await chunk_queue.get()
            if item is None:
                break
            stream, data = item
            await emit(stream, data)

    emit_task = asyncio.create_task(emit_loop())

    async def flush_emit() -> None:
        chunk_queue.put_nowait(None)
        await asyncio.gather(emit_task, return_exceptions=True)

    def on_output(stream: str, data: str) -> None:
        chunk_queue.put_nowait((stream, data))

    # 3. Setup Work Dir
    # Per-request directory keeps the temp script name collision-free across
    # concurrent executions; the backend writes the script inside it.
    tmp_root = Path(gettempdir()) / f"pyflow_work_{request_id}"
    tmp_file = tmp_root / USER_CODE_FILENAME
    tmp_root.mkdir(parents=True, exist_ok=True)

    try:
        # 4. Run Through the Configured Backend
        # The backend owns the child process (spawn, stdin, timeout kill,
        # truncation tracking) and returns raw, unprocessed output.
        raw = await get_backend().run(
            code=script,
            stdin=stdin,
            timeout_seconds=timeout_seconds,
            max_output_chars=max_output_chars,
            cwd=str(tmp_root),
            on_output=on_output,
        )

        # All reads are done: deliver remaining chunks, then stop the bridge.
        await flush_emit()

        elapsed_ms = int((time.time() - start_time) * 1000)

        # 5. Handle Timeout
        if raw.timed_out:
            # If output was already over the limit, report truncation,
            # not timeout (the process was killed for flooding, not hanging).
            if raw.output_truncated:
                return RunResponse(
                    status="error",
                    stdout="",
                    stderr="Output limit exceeded; process terminated.",
                    exit_code=None,
                    execution_time_ms=elapsed_ms,
                    output_truncated=True,
                    diagnostics=create_output_limit_diagnostics(),
                    request_id=request_id,
                )

            return RunResponse(
                status="timeout",
                stdout="",
                stderr=f"Tempo limite atingido ({timeout_seconds}s).",
                exit_code=None,
                execution_time_ms=elapsed_ms,
                output_truncated=False,
                diagnostics=create_timeout_diagnostics(timeout_seconds),
                request_id=request_id
            )

        # 6. Check Output Limits
        if raw.output_truncated:
            stdout_str, stderr_str = raw.stdout, raw.stderr

            # Rich output: pull any complete or partial images marker out of
            # the truncated streams, mirroring the finalize branch below.
            images = []
            if rich_output:
                stdout_str, images = _extract_images(stdout_str)
                stderr_str, _ = _extract_images(stderr_str)

            # Never leak the server temp path, even in a truncated chunk.
            stdout_str = _sanitize_output(stdout_str, tmp_file)
            stderr_str = _sanitize_output(stderr_str, tmp_file)
            return RunResponse(
                status="error",
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=raw.exit_code,
                execution_time_ms=elapsed_ms,
                output_truncated=True,
                images=images,
                diagnostics=create_output_limit_diagnostics(),
                request_id=request_id
            )

        # 7. Finalize Success/Error
        status = "success" if raw.exit_code == 0 else "error"
        diagnostics = None

        if status == "error":
            # Parse diagnostics
            diagnostics = parse_traceback_str(raw.stderr, tmp_file.name, include_raw=include_raw_traceback)
            if diagnostics and diagnostics.message:
                diagnostics.message = _sanitize_output(diagnostics.message, tmp_file)

        # Rich output: pull the base64 figures marker out before sanitizing,
        # so the marker never reaches the visible stdout.
        images = []
        if rich_output:
            raw.stdout, images = _extract_images(raw.stdout)

        # Never leak the server temp path in any branch; replace it with a
        # generic placeholder. Parsing happens first so the real filename can
        # still locate the user's frame, and raw_traceback keeps its
        # unsanitized-on-request contract.
        stdout_str = _sanitize_output(raw.stdout, tmp_file)
        stderr_str = _sanitize_output(raw.stderr, tmp_file)

        return RunResponse(
            status=status,
            stdout=stdout_str,
            stderr=stderr_str,
            exit_code=raw.exit_code,
            execution_time_ms=elapsed_ms,
            output_truncated=False,
            diagnostics=diagnostics,
            images=images,
            request_id=request_id
        )

    except NotImplementedError as e:
        # Backends surface unsupported-feature constraints (e.g. docker mode
        # v1 rejects stdin); return a clear error instead of masking it as an
        # internal failure.
        elapsed_ms = int((time.time() - start_time) * 1000)
        await flush_emit()
        return RunResponse(
            status="error",
            stdout="",
            stderr=str(e),
            exit_code=255,
            execution_time_ms=elapsed_ms,
            output_truncated=False,
            diagnostics=Diagnostics(error_type="BackendUnsupported", message=str(e)),
            request_id=request_id
        )

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.exception("Internal execution error")
        await flush_emit()
        # Never surface the server temp path in an internal error: route
        # the message through the same sanitization as the normal branches.
        sanitized_message = _sanitize_output(str(e), tmp_file)
        return RunResponse(
            status="error",
            stdout="",
            stderr=f"Internal Server Error: {sanitized_message}",
            exit_code=255,
            execution_time_ms=elapsed_ms,
            output_truncated=False,
            diagnostics=Diagnostics(error_type="InternalError", message=sanitized_message),
            request_id=request_id
        )
        
    finally:
        # A cancelled request (client disconnect) leaves the emit loop and the
        # child process running; the backend kills the child on its own
        # cancellation, so here we only stop the bridge and clean up.
        if not emit_task.done():
            emit_task.cancel()
            await asyncio.gather(emit_task, return_exceptions=True)

        # Cleanup the per-request work dir (script + any user-created files).
        try:
            shutil.rmtree(tmp_root, ignore_errors=True)
        except Exception:
            pass


async def execute_code(
    request_id: str,
    code: str,
    stdin: Optional[str],
    timeout_seconds: int,
    max_output_chars: int,
    include_raw_traceback: bool = False,
    rich_output: bool = False
) -> RunResponse:
    """
    Executes Python code through the configured backend without streaming.

    Thin wrapper over execute_code_stream with emit disabled.

    Args:
        request_id: Unique identifier for the request.
        code: Python code to execute.
        stdin: Standard input for the code (optional).
        timeout_seconds: Maximum execution time in seconds.
        max_output_chars: Maximum number of output characters.
        include_raw_traceback: Whether to include the full (unsanitized)
            traceback in diagnostics.
        rich_output: Whether to collect matplotlib figures as base64 images.

    Returns:
        RunResponse: Execution result with status, outputs and diagnostics.
    """
    return await execute_code_stream(
        request_id=request_id,
        code=code,
        stdin=stdin,
        timeout_seconds=timeout_seconds,
        max_output_chars=max_output_chars,
        include_raw_traceback=include_raw_traceback,
        rich_output=rich_output,
    )
