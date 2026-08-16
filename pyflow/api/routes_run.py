"""
Rota de execução de código Python do PyFlow.

Este módulo define o endpoint /run que permite executar
código Python em um ambiente isolado e seguro.

O endpoint suporta:
    - Execução de código com timeout configurável
    - Entrada stdin para programas interativos
    - Limite de caracteres na saída
    - Diagnósticos estruturados de erros
    - Explicação de erros via IA (opcional)

A execução ocorre em um subprocesso isolado para segurança.
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pyflow.core.models import RunRequest, RunResponse
from pyflow.core.config import settings
from pyflow.core.engine import execute_code
from pyflow.core.ai_service import AIService
from pyflow.utils.ids import generate_request_id
from pyflow.api.deps import require_local_origin, require_token

router = APIRouter()

_run_semaphore = asyncio.Semaphore(settings.PYFLOW_MAX_CONCURRENT_RUNS)


@router.post("/run", response_model=RunResponse, dependencies=[Depends(require_token), Depends(require_local_origin)])
async def run_code_endpoint(req: RunRequest):
    """
    Executa código Python e retorna o resultado.

    Recebe código Python, executa em um subprocesso isolado com
    timeout e limites configurados, e retorna stdout, stderr,
    diagnósticos de erros e opcionalmente explicação de IA.

    Args:
        req: Requisição contendo código, stdin, configurações e opções de IA.

    Returns:
        RunResponse: Resultado da execução com status, saídas e diagnósticos.

    Note:
        - O limite de código é verificado antes da execução.
        - Se ai_explain_on_error=True e ocorrer erro, a IA é consultada.
        - Paths no traceback são sanitizados por segurança.
    """
    if _run_semaphore.locked():
        raise HTTPException(
            status_code=429,
            detail="Too many concurrent executions",
            headers={"Retry-After": "1"},
        )

    async with _run_semaphore:
        request_id = generate_request_id()

        # Defaults
        timeout = req.timeout_seconds or settings.PYFLOW_DEFAULT_TIMEOUT_SECONDS
        max_output = req.max_output_chars or settings.PYFLOW_MAX_OUTPUT_CHARS_DEFAULT

        # Hard limit on output chars to prevent memory issues
        if max_output > settings.PYFLOW_MAX_OUTPUT_CHARS_MAX:
            max_output = settings.PYFLOW_MAX_OUTPUT_CHARS_MAX

        # Verify code length (simple check)
        if len(req.code) > settings.PYFLOW_MAX_CODE_CHARS:
            # We could return 400, but spec says "Enforce... limit of size".
            # RunResponse has "status". Let's use error status.
            # But usually pre-validation is better.
            # For now, let's treat as a quick execution error.
            from pyflow.core.models import Diagnostics
            return RunResponse(
                status="error",
                stdout="",
                stderr=f"Code size exceeds limit ({settings.PYFLOW_MAX_CODE_CHARS} chars).",
                exit_code=1,
                execution_time_ms=0,
                output_truncated=False,
                diagnostics=Diagnostics(error_type="CodeTooLarge", message="O código é muito grande."),
                request_id=request_id
            )

        # Execute
        result = await execute_code(
            request_id=request_id,
            code=req.code,
            stdin=req.stdin,
            timeout_seconds=timeout,
            max_output_chars=max_output,
            include_raw_traceback=req.include_raw_traceback,
            rich_output=req.rich_output
        )

        # Sanitize traceback path if strictly raw is not requested,
        # but diagnostics.py already handles sanitization in diagnostics.context/message.
        # result.stderr contains the full traceback.
        # RF-06: "Deve sanitizar paths no traceback".
        from pyflow.core.diagnostics import sanitize_path
        result.stderr = sanitize_path(result.stderr)

        # AI Explanation
        if req.ai_explain_on_error and result.status == "error" and result.diagnostics and req.ai_config:
            try:
                ai_help = await AIService.explain_error(
                    code=req.code,
                    stderr=result.stderr,
                    diagnostics=result.diagnostics,
                    config=req.ai_config
                )
                result.ai_error_help = ai_help
            except Exception:
                # Silent fail for IA as per spec
                pass

        return result
