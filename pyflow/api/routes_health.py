"""
Rota de verificação de saúde do PyFlow.

Este módulo define o endpoint /health que permite verificar
se o serviço PyFlow está em execução e obter informações
básicas sobre ele.

O endpoint é útil para:
    - Monitoramento de disponibilidade do serviço
    - Descoberta automática por clientes (UI)
    - Verificação de versão do serviço
"""

import os
import time
from fastapi import APIRouter
from pyflow.core.models import HealthResponse
from pyflow import __version__

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Verifica a saúde do serviço PyFlow.

    Retorna informações sobre o status atual do serviço,
    incluindo versão, PID do processo e timestamp.

    Returns:
        HealthResponse: Status e informações do serviço.
    """
    return HealthResponse(
        status="ok",
        service="pyflow",
        version=__version__,
        pid=os.getpid(),
        time=time.strftime("%Y-%m-%dT%H:%M:%S%z")
    )
