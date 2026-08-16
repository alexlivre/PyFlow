"""
Rota de dica socrática com IA do PyFlow.

Este módulo define o endpoint /hint que oferece orientação
progressiva (níveis 1 a 3) sobre o código do usuário.

O endpoint recebe:
    - Código atual do editor
    - Nível da dica (1 = pergunta-guia, 2 = localiza o problema,
      3 = quase-solução)
    - Diagnóstico do erro (opcional)
    - Configuração do provedor de IA

E retorna a dica gerada pela IA junto com o ID da requisição.
"""

from fastapi import APIRouter, Depends
from pyflow.core.models import HintRequest, HintResponse
from pyflow.core.ai_service import AIService
from pyflow.utils.ids import generate_request_id
from pyflow.api.deps import require_local_origin, require_token

router = APIRouter()


@router.post("/hint", response_model=HintResponse, dependencies=[Depends(require_token), Depends(require_local_origin)])
async def hint_endpoint(req: HintRequest):
    """
    Gera uma dica socrática para o código do usuário.

    Recebe o código, o nível de dica e opcionalmente o diagnóstico,
    envia para o modelo de IA configurado e retorna a orientação.

    Args:
        req: Requisição contendo código, nível, diagnóstico e config de IA.

    Returns:
        HintResponse: Dica da IA e ID da requisição.

    Note:
        Se ai_config não for fornecido, retorna mensagem de erro.
    """
    request_id = generate_request_id()

    # Validate that ai_config is provided
    if not req.ai_config:
        hint_text = "Erro: Nenhuma configuração de IA foi fornecida. Configure um modelo nas configurações."
    else:
        hint_text = await AIService.socratic_hint(
            code=req.code,
            diagnostics=req.diagnostics,
            level=req.level,
            config=req.ai_config,
        )

    return HintResponse(
        hint=hint_text,
        request_id=request_id
    )
