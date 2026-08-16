"""
Modelos de dados Pydantic do PyFlow.

Este módulo define todos os modelos de dados utilizados pela API,
incluindo requests, responses e tipos auxiliares.

Os modelos são organizados por endpoint:
    - AIConfig: Configuração de IA (compartilhado)
    - Diagnostics, AIErrorHelp: Diagnósticos de erros
    - RunRequest, RunResponse: Endpoint /run
    - ChatRequest, ChatResponse, ChatMessage: Endpoint /chat
    - HealthResponse: Endpoint /health

Todos os modelos utilizam Pydantic para validação automática
e serialização JSON.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict, Literal


# --- IA Config ---
class AIConfig(BaseModel):
    """
    Configuração de provedor de IA.

    Define as credenciais e configurações para se conectar
    a um provedor de IA (OpenAI, Gemini, Anthropic, etc).

    Attributes:
        provider: Nome do provedor (ex: 'openai', 'gemini').
        model_id: Identificador do modelo (ex: 'gpt-4', 'gemini-pro').
        api_key: Chave de API para autenticação (opcional).
        base_url: URL base da API para provedores customizados (opcional).
    """

    provider: str
    model_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


# --- Common / Diagnostics ---
class Diagnostics(BaseModel):
    """
    Informações de diagnóstico de erro.

    Contém informações estruturadas sobre um erro ocorrido
    durante a execução do código.

    Attributes:
        error_type: Tipo do erro (ex: 'NameError', 'SyntaxError').
        message: Mensagem descritiva do erro.
        line: Número da linha onde o erro ocorreu (opcional).
        context: Contexto adicional como snippet de código (opcional).
        raw_traceback: Traceback completo não sanitizado (opcional).
    """

    error_type: str
    message: str
    line: Optional[int] = None
    context: Optional[str] = None
    raw_traceback: Optional[str] = None


class AIErrorHelp(BaseModel):
    """
    Resposta da IA com ajuda sobre o erro.

    Contém a análise da IA sobre o erro e sugestões de correção.

    Attributes:
        summary: Resumo do erro em linguagem simples.
        probable_fix: Sugestão de como corrigir o erro.
        suggested_code: Código corrigido sugerido pela IA (opcional).
    """

    summary: str
    probable_fix: str
    suggested_code: Optional[str] = None


# --- Run Endpoint ---
class RunRequest(BaseModel):
    """
    Requisição para execução de código Python.

    Contém o código a ser executado e configurações opcionais
    para timeout, limites de saída e integração com IA.

    Attributes:
        code: Código Python a ser executado.
        stdin: Entrada padrão para o código (opcional).
        timeout_seconds: Tempo máximo de execução em segundos (opcional).
        max_output_chars: Limite máximo de caracteres na saída (opcional).
        include_raw_traceback: Se deve incluir traceback completo.
        ai_explain_on_error: Se deve solicitar explicação da IA em caso de erro.
        ai_config: Configuração do provedor de IA (opcional).
    """

    code: str
    stdin: Optional[str] = None
    timeout_seconds: Optional[int] = None
    max_output_chars: Optional[int] = None
    include_raw_traceback: bool = False
    ai_explain_on_error: bool = False
    ai_config: Optional[AIConfig] = None


class RunResponse(BaseModel):
    """
    Resposta da execução de código Python.

    Contém o resultado da execução, incluindo saídas, status,
    diagnósticos de erro e ajuda da IA.

    Attributes:
        status: Status da execução ('success', 'error', 'blocked', 'timeout').
        stdout: Saída padrão capturada.
        stderr: Saída de erro capturada.
        exit_code: Código de saída do processo (opcional).
        execution_time_ms: Tempo de execução em milissegundos.
        output_truncated: Se a saída foi truncada por exceder limite.
        diagnostics: Informações de diagnóstico de erro (opcional).
        ai_error_help: Ajuda da IA sobre o erro (opcional).
        request_id: Identificador único da requisição.
    """

    status: Literal["success", "error", "blocked", "timeout"]
    stdout: str
    stderr: str
    exit_code: Optional[int] = None
    execution_time_ms: int
    output_truncated: bool
    diagnostics: Optional[Diagnostics] = None
    ai_error_help: Optional[AIErrorHelp] = None
    request_id: str


# --- Chat Endpoint ---
class ChatMessage(BaseModel):
    """
    Mensagem individual do chat.

    Representa uma mensagem no histórico de conversa.

    Attributes:
        role: Papel do autor ('user' ou 'assistant').
        content: Conteúdo da mensagem.
    """

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """
    Requisição para chat com IA.

    Contém a mensagem do usuário, contexto de código e histórico.

    Attributes:
        code: Código atual no editor para contexto (opcional).
        user_message: Mensagem do usuário.
        history: Histórico de mensagens anteriores.
        ai_config: Configuração do provedor de IA (opcional).
    """

    code: Optional[str] = None
    user_message: str
    history: List[ChatMessage] = []
    ai_config: Optional[AIConfig] = None
    mode: Optional[Literal["tutor", "hint"]] = None


class ChatResponse(BaseModel):
    """
    Resposta do chat com IA.

    Contém a resposta da IA e o histórico atualizado.

    Attributes:
        reply: Resposta da IA.
        history: Histórico completo incluindo a nova interação.
        request_id: Identificador único da requisição.
    """

    reply: str
    history: List[ChatMessage]
    request_id: str


# --- Hint Endpoint ---
class HintRequest(BaseModel):
    """
    Requisição de dica socrática com IA.

    Contém o código, o nível de dica (1 a 3) e o diagnóstico do erro.

    Attributes:
        code: Código Python atual no editor.
        level: Nível da dica (1 = pergunta-guia, 2 = localiza o problema,
            3 = quase-solução).
        diagnostics: Diagnóstico do erro (opcional).
        ai_config: Configuração do provedor de IA (opcional).
    """

    code: str
    level: int = Field(1, ge=1, le=3)
    diagnostics: Optional[Diagnostics] = None
    ai_config: Optional[AIConfig] = None


class HintResponse(BaseModel):
    """
    Resposta de dica socrática da IA.

    Attributes:
        hint: Dica gerada pela IA.
        request_id: Identificador único da requisição.
    """

    hint: str
    request_id: str


# --- Health Endpoint ---
class HealthResponse(BaseModel):
    """
    Resposta do endpoint de saúde.

    Contém informações sobre o status do serviço.

    Attributes:
        status: Status do serviço ('ok').
        service: Nome do serviço ('pyflow').
        version: Versão do PyFlow.
        pid: ID do processo do servidor.
        time: Timestamp atual (opcional).
    """

    status: str
    service: str
    version: str
    pid: int
    time: Optional[str] = None
