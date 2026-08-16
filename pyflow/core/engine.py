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
import sys
import os
import psutil
from pathlib import Path
from tempfile import gettempdir
from typing import Awaitable, Callable, Optional, Tuple
from loguru import logger
import time

from pyflow.core.config import settings
from pyflow.core.models import RunResponse, Diagnostics
from pyflow.core.diagnostics import (
    parse_traceback_str,
    create_blocked_diagnostics,
    create_timeout_diagnostics,
    create_output_limit_diagnostics,
)


def _sanitize_output(text: str, tmp_file: Path) -> str:
    """Replace the temp-file path in output with a generic placeholder."""
    return text.replace(str(tmp_file), "<user_code>")


async def _read_stream(
    stream: asyncio.StreamReader,
    limit: int,
    on_chunk: Optional[Callable[[str], None]] = None,
) -> Tuple[str, bool]:
    """
    Reads chunks from an async stream up to a character limit.

    Each decoded chunk is passed to on_chunk (when provided) before the
    limit check, so streaming consumers see the raw output as it arrives.

    Args:
        stream: Async StreamReader (stdout or stderr).
        limit: Maximum number of characters to read.
        on_chunk: Optional callback invoked with each decoded chunk
            before the limit is applied.

    Returns:
        Tuple containing:
            - str: Content read from the stream.
            - bool: True if the content was truncated by the limit.
    """
    output = []
    total_chars = 0
    truncated = False

    while True:
        # Read small chunks
        chunk = await stream.read(4096)
        if not chunk:
            break

        decoded = chunk.decode("utf-8", errors="replace")
        if on_chunk is not None:
            on_chunk(decoded)

        chunk_len = len(decoded)

        if total_chars + chunk_len > limit:
            remaining = limit - total_chars
            output.append(decoded[:remaining])
            truncated = True
            break

        output.append(decoded)
        total_chars += chunk_len

    return "".join(output), truncated


def _build_child_env() -> dict:
    """Build a minimal env for the child process.

    A whitelist prevents user code from reading server secrets
    (API keys, tokens) and keeps the execution environment clean.
    """
    return {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    }


def _kill_process_tree(pid: int):
    """
    Termina um processo e todos os seus processos filhos.

    Utiliza psutil para encontrar e encerrar recursivamente
    todos os processos na árvore de processos.

    Args:
        pid: ID do processo pai a terminar.

    Note:
        Exceções NoSuchProcess são silenciadas caso o processo
        já tenha sido encerrado.
    """
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass


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
    include_raw_traceback: bool = False
) -> RunResponse:
    """
    Executa código Python em um subprocesso isolado.

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

    def make_on_chunk(stream: str) -> Callable[[str], None]:
        def on_chunk(data: str) -> None:
            chunk_queue.put_nowait((stream, data))
        return on_chunk

    # 3. Setup Temp File
    tmp_dir = Path(gettempdir())
    tmp_file = tmp_dir / f"pyflow_tmp_{request_id}.py"

    process = None
    try:
        tmp_file.write_text(code, encoding="utf-8")
        
        # 3. Create Subprocess
        # Use -u for unbuffered output to catch prints immediately
        # Use sys.executable to ensure we use the same python interpreter (or standard one)
        # Spec says: "Rodar snippets Python". Localhost environment.
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-u", str(tmp_file),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(tmp_dir), # Run in temp dir to avoid polluting project dir
            env=_build_child_env()
        )
        
        # Write stdin if provided
        if stdin is not None:
            if process.stdin:
                try:
                    process.stdin.write(stdin.encode("utf-8"))
                    await process.stdin.drain()
                    process.stdin.close()
                except Exception as e:
                    logger.warning(f"Error writing to stdin: {e}")

        # 4. Read Output with Limits
        # We need to run reading tasks concurrently
        read_stdout_task = asyncio.create_task(
            _read_stream(process.stdout, max_output_chars, on_chunk=make_on_chunk("stdout"))
        )
        read_stderr_task = asyncio.create_task(
            _read_stream(process.stderr, max_output_chars, on_chunk=make_on_chunk("stderr"))
        )
        
        wait_process_task = asyncio.create_task(process.wait())
        
        # 5. Handle Timeout
        # Wait until the process finishes AND both reads complete, or timeout.
        # A read task may complete early when the output limit is hit while
        # the process keeps running; that must be reported as truncation,
        # not as a timeout.
        done, pending = await asyncio.wait(
            [wait_process_task, read_stdout_task, read_stderr_task],
            timeout=timeout_seconds,
            return_when=asyncio.ALL_COMPLETED,
        )
        
        # Check if process is still running (Timeout case)
        if process.returncode is None and not wait_process_task.done():
            _kill_process_tree(process.pid)

            # Close the pipe transports so process.wait() can resolve.
            # On Windows a pipe with no pending read/write never reports
            # disconnection, so the exit waiters would never be woken up.
            transport = process._transport
            if transport is not None:
                for fd in (0, 1, 2):
                    pipe = transport.get_pipe_transport(fd)
                    if pipe is not None:
                        pipe.close()

            try:
                await process.wait()
            except Exception:
                pass

            # Cancel read tasks
            read_stdout_task.cancel()
            read_stderr_task.cancel()

            # Deliver any chunks read before cancellation, then stop the bridge.
            await flush_emit()

            # If output was already over the limit, report truncation,
            # not timeout (the process was killed for flooding, not hanging).
            stdout_trunc = (
                read_stdout_task.done()
                and not read_stdout_task.cancelled()
                and read_stdout_task.result()[1]
            )
            stderr_trunc = (
                read_stderr_task.done()
                and not read_stderr_task.cancelled()
                and read_stderr_task.result()[1]
            )

            elapsed_ms = int((time.time() - start_time) * 1000)
            if stdout_trunc or stderr_trunc:
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

        # Process finished, await reading tasks to get full output
        # (There's a chance tasks are not done if process finished very fast?, no, process.wait() is done)
        # But reading tasks might still be buffering bytes.
        try:
            stdout_str, stdout_trunc = await read_stdout_task
            stderr_str, stderr_trunc = await read_stderr_task
        except asyncio.CancelledError:
             # Should not happen if process finished gracefully
             stdout_str, stdout_trunc = "", False
             stderr_str, stderr_trunc = "", False

        # All reads are done: deliver remaining chunks, then stop the bridge.
        await flush_emit()

        elapsed_ms = int((time.time() - start_time) * 1000)

        # 6. Check Output Limits
        if stdout_trunc or stderr_trunc:
             # If truncated, we should ensure process is dead (although stream reading stops)
             # If processed finished by itself but output was huge? 
             # Or if we stopped reading?
             # Logic above: _read_stream stops reading and returns. process might still be writing?
             if process.returncode is None:
                 _kill_process_tree(process.pid)
            
             # Never leak the server temp path, even in a truncated chunk.
             stdout_str = _sanitize_output(stdout_str, tmp_file)
             stderr_str = _sanitize_output(stderr_str, tmp_file)
             return RunResponse(
                status="error",
                stdout=stdout_str + ("\n(truncado)" if stdout_trunc else ""),
                stderr=stderr_str + ("\n(truncado)" if stderr_trunc else ""),
                exit_code=process.returncode,
                execution_time_ms=elapsed_ms,
                output_truncated=True,
                diagnostics=create_output_limit_diagnostics(),
                request_id=request_id
            )
            
        # 7. Finalize Success/Error
        status = "success" if process.returncode == 0 else "error"
        diagnostics = None
        
        if status == "error":
            # Parse diagnostics
            diagnostics = parse_traceback_str(stderr_str, tmp_file.name, include_raw=include_raw_traceback)
            if diagnostics and diagnostics.message:
                diagnostics.message = _sanitize_output(diagnostics.message, tmp_file)

        # Never leak the server temp path in any branch; replace it with a
        # generic placeholder. Parsing happens first so the real filename can
        # still locate the user's frame, and raw_traceback keeps its
        # unsanitized-on-request contract.
        stdout_str = _sanitize_output(stdout_str, tmp_file)
        stderr_str = _sanitize_output(stderr_str, tmp_file)

        return RunResponse(
            status=status,
            stdout=stdout_str,
            stderr=stderr_str,
            exit_code=process.returncode,
            execution_time_ms=elapsed_ms,
            output_truncated=False,
            diagnostics=diagnostics,
            request_id=request_id
        )

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.exception("Internal execution error")
        await flush_emit()
        return RunResponse(
            status="error",
            stdout="",
            stderr=f"Internal Server Error: {e}",
            exit_code=255,
            execution_time_ms=elapsed_ms,
            output_truncated=False,
            diagnostics=Diagnostics(error_type="InternalError", message=str(e)),
            request_id=request_id
        )
        
    finally:
        # A cancelled request (client disconnect) leaves the emit loop and the
        # child process running; stop both before unwinding.
        if not emit_task.done():
            emit_task.cancel()
            await asyncio.gather(emit_task, return_exceptions=True)
        if process is not None and process.returncode is None:
            try:
                _kill_process_tree(process.pid)
            except Exception:
                pass

        # Cleanup
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except Exception:
                pass


async def execute_code(
    request_id: str,
    code: str,
    stdin: Optional[str],
    timeout_seconds: int,
    max_output_chars: int,
    include_raw_traceback: bool = False
) -> RunResponse:
    """
    Executes Python code in an isolated subprocess without streaming.

    Thin wrapper over execute_code_stream with emit disabled.

    Args:
        request_id: Unique identifier for the request.
        code: Python code to execute.
        stdin: Standard input for the code (optional).
        timeout_seconds: Maximum execution time in seconds.
        max_output_chars: Maximum number of output characters.
        include_raw_traceback: Whether to include the full (unsanitized)
            traceback in diagnostics.

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
    )
