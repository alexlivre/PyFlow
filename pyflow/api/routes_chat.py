"""
Rota de chat com IA do PyFlow.

Este módulo define o endpoint /chat que permite interação
conversacional com modelos de IA, incluindo contexto de código.

O endpoint recebe:
    - Mensagem do usuário
    - Código atual (opcional, para contexto)
    - Histórico de conversa
    - Configuração do provedor de IA

E retorna a resposta da IA junto com o histórico atualizado.
"""

from fastapi import APIRouter, Depends
from pyflow.core.models import ChatRequest, ChatResponse, ChatMessage
from pyflow.core.ai_service import AIService
from pyflow.utils.ids import generate_request_id
from pyflow.api.deps import require_local_origin, require_token

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_token), Depends(require_local_origin)])
async def chat_endpoint(req: ChatRequest):
    """
    Processa uma mensagem de chat com IA.

    Recebe a mensagem do usuário, opcionalmente com código para contexto,
    envia para o modelo de IA configurado e retorna a resposta.

    Args:
        req: Requisição contendo mensagem, código, histórico e config de IA.

    Returns:
        ChatResponse: Resposta da IA e histórico atualizado.

    Note:
        Se ai_config não for fornecido, retorna mensagem de erro.
    """
    request_id = generate_request_id()

    # Validate that ai_config is provided
    if not req.ai_config:
        reply_text = "Erro: Nenhuma configuração de IA foi fornecida. Configure um modelo nas configurações."
    else:
        reply_text = await AIService.chat(
            code=req.code,
            user_message=req.user_message,
            history=req.history,
            config=req.ai_config
        )

    # Update history
    new_history = list(req.history)
    new_history.append(ChatMessage(role="user", content=req.user_message))
    new_history.append(ChatMessage(role="assistant", content=reply_text))

    return ChatResponse(
        reply=reply_text,
        history=new_history,
        request_id=request_id
    )
