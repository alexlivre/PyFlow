"""
Streaming code-execution endpoint (NDJSON events).

Mirrors the /run endpoint but streams stdout/stderr chunks as they are
produced by the child process. The response is a stream of newline-delimited
JSON events:

    {"type": "status", "status": "running"}
    {"type": "output", "stream": "stdout", "data": "<chunk>"}
    {"type": "done", "result": {RunResponse}}

On internal failure an error event is emitted instead of done:
    {"type": "error", "message": "..."}
"""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

from pyflow.api.deps import require_local_origin, require_token
from pyflow.api.routes_run import _run_semaphore
from pyflow.core.ai_service import AIService
from pyflow.core.config import settings
from pyflow.core.diagnostics import sanitize_path
from pyflow.core.engine import execute_code_stream
from pyflow.core.models import Diagnostics, RunRequest, RunResponse
from pyflow.utils.ids import generate_request_id

router = APIRouter()


@router.post("/run/stream", dependencies=[Depends(require_token), Depends(require_local_origin)])
async def run_stream_endpoint(req: RunRequest) -> StreamingResponse:
    """Execute Python code, streaming stdout/stderr chunks as NDJSON events."""
    # Atomic non-blocking acquire: rejects the extra request with 429 instead
    # of queueing behind the lock (no TOCTOU race, no hang on bursts).
    if not _run_semaphore.acquire_nowait():
        raise HTTPException(
            status_code=429,
            detail="Too many concurrent executions",
            headers={"Retry-After": "1"},
        )
    # The slot is released in the generator's finally block, which also runs
    # on client disconnect and on early errors below.
    try:
        return StreamingResponse(event_source(req), media_type="application/x-ndjson")
    except Exception:
        _run_semaphore.release()
        raise


async def event_source(req: RunRequest):
    request_id = generate_request_id()
    logger.bind(request_id=request_id).info("run:start", code_chars=len(req.code))

    # Defaults
    timeout = req.timeout_seconds or settings.PYFLOW_DEFAULT_TIMEOUT_SECONDS
    max_output = req.max_output_chars or settings.PYFLOW_MAX_OUTPUT_CHARS_DEFAULT

    # Hard limit on output chars to prevent memory issues
    if max_output > settings.PYFLOW_MAX_OUTPUT_CHARS_MAX:
        max_output = settings.PYFLOW_MAX_OUTPUT_CHARS_MAX

    try:
        events = asyncio.Queue()
        events.put_nowait(
            json.dumps({"type": "status", "status": "running"}, ensure_ascii=False) + "\n"
        )

        async def emit(stream: str, data: str) -> None:
            if not data:
                return
            events.put_nowait(
                json.dumps({"type": "output", "stream": stream, "data": data}, ensure_ascii=False) + "\n"
            )

        async def runner():
            try:
                if len(req.code) > settings.PYFLOW_MAX_CODE_CHARS:
                    result = RunResponse(
                        status="error",
                        stdout="",
                        stderr=f"Code size exceeds limit ({settings.PYFLOW_MAX_CODE_CHARS} chars).",
                        exit_code=1,
                        execution_time_ms=0,
                        output_truncated=False,
                        diagnostics=Diagnostics(error_type="CodeTooLarge", message="O código é muito grande."),
                        request_id=request_id,
                    )
                else:
                    result = await execute_code_stream(
                        request_id=request_id,
                        code=req.code,
                        stdin=req.stdin,
                        timeout_seconds=timeout,
                        max_output_chars=max_output,
                        emit=emit,
                        include_raw_traceback=req.include_raw_traceback,
                    )
                    # Same path sanitization contract as /run: strip any
                    # remaining server paths from the displayed stderr.
                    result.stderr = sanitize_path(result.stderr)

                # AI Explanation (same contract as /run)
                if req.ai_explain_on_error and result.status == "error" and result.diagnostics and req.ai_config:
                    try:
                        ai_help = await AIService.explain_error(
                            code=req.code,
                            stderr=result.stderr,
                            diagnostics=result.diagnostics,
                            config=req.ai_config,
                        )
                        result.ai_error_help = ai_help
                    except Exception:
                        # Silent fail for AI as per spec
                        pass

                logger.bind(request_id=request_id).info(
                    "run:done", status=result.status, duration_ms=result.execution_time_ms
                )
                events.put_nowait(
                    json.dumps(
                        {"type": "done", "result": json.loads(result.model_dump_json())},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            except Exception as exc:
                events.put_nowait(
                    json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n"
                )
            finally:
                events.put_nowait(None)

        runner_task = asyncio.create_task(runner())
        try:
            while True:
                event = await events.get()
                if event is None:
                    break
                yield event
        finally:
            # Client disconnected: stop the runner so the child is reaped.
            runner_task.cancel()
            await asyncio.gather(runner_task, return_exceptions=True)
    finally:
        # Always release the slot when the stream ends, including disconnects.
        _run_semaphore.release()
