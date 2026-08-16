"""
Helpers compartilhados entre os backends de execução.

Contém a coreografia comum de processo assíncrono (escrita de stdin,
leitura com limite, wait com timeout, kill em árvore) usada tanto pelo
backend de subprocesso quanto pelo backend Docker.
"""

import asyncio
import psutil
from typing import Callable, Optional, Tuple
from loguru import logger

from pyflow.core.backends.base import RawExecution


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


def _sanitize_output(text: str, tmp_file) -> str:
    """Replace the temp-file path in output with a generic placeholder."""
    return text.replace(str(tmp_file), "<user_code>")


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


async def _execute_process(
    process: asyncio.subprocess.Process,
    stdin_payload: Optional[str],
    timeout_seconds: int,
    max_output_chars: int,
    on_output: Optional[Callable[[str, str], None]] = None,
) -> RawExecution:
    """Coreografia comum de execução de um processo já iniciado.

    Escreve `stdin_payload` (quando fornecida) e fecha o pipe antes de
    ler, aguarda o processo com timeout, mata a árvore em caso de
    estouro e aplica o limite de caracteres por stream.

    Args:
        process: Processo assíncrono já iniciado (stdin/stdout/stderr
            conectados via PIPE).
        stdin_payload: Payload a escrever no stdin (None para não escrever).
        timeout_seconds: Tempo máximo de execução em segundos.
        max_output_chars: Limite máximo de caracteres por stream.
        on_output: Callback síncrono (stream, chunk) para streaming.

    Returns:
        RawExecution com saídas limitadas, exit code e flags de
        timeout/truncamento.
    """
    if stdin_payload is not None:
        if process.stdin:
            try:
                process.stdin.write(stdin_payload.encode("utf-8"))
                await process.stdin.drain()
                process.stdin.close()
            except Exception as e:
                logger.warning(f"Error writing to stdin: {e}")

    def make_on_chunk(stream: str) -> Callable[[str], None]:
        def on_chunk(data: str) -> None:
            if on_output is not None:
                on_output(stream, data)
        return on_chunk

    # We need to run reading tasks concurrently
    read_stdout_task = asyncio.create_task(
        _read_stream(process.stdout, max_output_chars, on_chunk=make_on_chunk("stdout"))
    )
    read_stderr_task = asyncio.create_task(
        _read_stream(process.stderr, max_output_chars, on_chunk=make_on_chunk("stderr"))
    )

    wait_process_task = asyncio.create_task(process.wait())

    try:
        # Wait until the process finishes AND both reads complete, or timeout.
        # A read task may complete early when the output limit is hit while
        # the process keeps running; that must be reported as truncation,
        # not as a timeout.
        await asyncio.wait(
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

            return RawExecution(
                stdout="",
                stderr="",
                exit_code=None,
                timed_out=True,
                output_truncated=stdout_trunc or stderr_trunc,
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

        if stdout_trunc or stderr_trunc:
            # If truncated, we should ensure process is dead (although stream reading stops)
            # If processed finished by itself but output was huge?
            # Or if we stopped reading?
            if process.returncode is None:
                _kill_process_tree(process.pid)

            if stdout_trunc:
                stdout_str += "\n(truncado)"
            if stderr_trunc:
                stderr_str += "\n(truncado)"

            return RawExecution(
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=process.returncode,
                timed_out=False,
                output_truncated=True,
            )

        return RawExecution(
            stdout=stdout_str,
            stderr=stderr_str,
            exit_code=process.returncode,
            timed_out=False,
            output_truncated=False,
        )
    finally:
        # A cancelled wait (client disconnect) must not leave the child
        # running; kill the tree before unwinding.
        if process.returncode is None:
            try:
                _kill_process_tree(process.pid)
            except Exception:
                pass
        # Drop orphaned readers/waiter so no task outlives the backend call.
        for task in (read_stdout_task, read_stderr_task, wait_process_task):
            if not task.done():
                task.cancel()
