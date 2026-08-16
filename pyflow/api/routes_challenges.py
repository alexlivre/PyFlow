"""
Rotas de desafios com verificação automática (mini-Judge0).

Este módulo define os endpoints:
    - GET /challenges: catálogo público dos desafios disponíveis.
    - POST /challenges/run: executa o código do aluno contra os testes
      ocultos do desafio.

Ambos os endpoints são protegidos por token e origem local.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from pyflow.api.deps import require_local_origin, require_token
from pyflow.core.challenges import ChallengeNotFoundError, list_challenge_infos, run_challenge
from pyflow.core.config import settings
from pyflow.core.models import ChallengeInfo, ChallengeResult, ChallengeRunRequest

router = APIRouter()


@router.get(
    "/challenges",
    response_model=List[ChallengeInfo],
    dependencies=[Depends(require_token), Depends(require_local_origin)],
)
async def list_challenges_endpoint():
    """List the available challenges with their public metadata."""
    return list_challenge_infos()


@router.post(
    "/challenges/run",
    response_model=ChallengeResult,
    dependencies=[Depends(require_token), Depends(require_local_origin)],
)
async def run_challenge_endpoint(req: ChallengeRunRequest):
    """Run the student code against a challenge's hidden tests."""
    if len(req.code) > settings.PYFLOW_MAX_CODE_CHARS:
        raise HTTPException(status_code=400, detail="Code size exceeds limit.")

    timeout = req.timeout_seconds or settings.PYFLOW_DEFAULT_TIMEOUT_SECONDS
    try:
        return await run_challenge(
            code=req.code, challenge_id=req.challenge_id, timeout_seconds=timeout
        )
    except ChallengeNotFoundError:
        raise HTTPException(status_code=404, detail="Challenge not found")
