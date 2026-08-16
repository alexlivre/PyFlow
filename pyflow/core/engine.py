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
from typing import Tuple, Optional
from loguru import logger
import time

from pyflow.core.config import settings
from pyflow.core.models import RunResponse, Diagnostics
from pyflow.core.diagnostics import (
    parse_traceback_str,
    create_blocked_diagnostics,
    create_timeout_diagnostics,
    create_output_limit_diagnostics,
    sanitize_path
)


async def _read_stream(stream: asyncio.StreamReader, limit: int) -> Tuple[str, bool]:
    """
    Lê dados de um stream assíncrono até o limite especificado.

    Lê chunks do stream até que o limite de caracteres seja atingido
    ou o stream seja fechado.

    Args:
        stream: StreamReader assíncrono (stdout ou stderr).
        limit: Limite máximo de caracteres a ler.

    Returns:
        Tuple contendo:
            - str: Conteúdo lido do stream.
            - bool: True se o conteúdo foi truncado por atingir o limite.
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


async def execute_code(
    request_id: str,
    code: str,
    stdin: Optional[str],
    timeout_seconds: int,
    max_output_chars: int
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

    # 2. Setup Temp File
    tmp_dir = Path(gettempdir())
    tmp_file = tmp_dir / f"pyflow_tmp_{request_id}.py"
    
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
        read_stdout_task = asyncio.create_task(_read_stream(process.stdout, max_output_chars))
        read_stderr_task = asyncio.create_task(_read_stream(process.stderr, max_output_chars))
        
        wait_process_task = asyncio.create_task(process.wait())
        
        # 5. Handle Timeout
        # We wait for either process to finish OR timeout
        done, pending = await asyncio.wait(
            [wait_process_task, read_stdout_task, read_stderr_task],
            timeout=timeout_seconds,
            return_when=asyncio.FIRST_EXCEPTION # Wait for all unless error? No, we needed timeout.
            # actually asyncio.wait with timeout doesn't kill tasks automatically.
        )
        
        # Check if process is still running (Timeout case)
        if process.returncode is None and not wait_process_task.done():
            _kill_process_tree(process.pid)
            try: 
                await process.wait() 
            except: 
                pass
            
            # Cancel read tasks
            read_stdout_task.cancel()
            read_stderr_task.cancel()
            
            elapsed_ms = int((time.time() - start_time) * 1000)
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

        elapsed_ms = int((time.time() - start_time) * 1000)

        # 6. Check Output Limits
        if stdout_trunc or stderr_trunc:
             # If truncated, we should ensure process is dead (although stream reading stops)
             # If processed finished by itself but output was huge? 
             # Or if we stopped reading?
             # Logic above: _read_stream stops reading and returns. process might still be writing?
             if process.returncode is None:
                 _kill_process_tree(process.pid)
            
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
            diagnostics = parse_traceback_str(stderr_str, tmp_file.name)
            
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
        # Cleanup
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except Exception:
                pass
