"""
Configurações centralizadas do PyFlow.

Este módulo define todas as configurações do PyFlow utilizando Pydantic Settings.
As configurações podem ser definidas via variáveis de ambiente ou arquivo .env.

Categorias de configuração:
    - Rede/Servidor: Host, porta e busca de porta
    - Execução: Timeout, limites de código e saída
    - IA: Tokens máximos e temperatura
    - API Keys: Chaves de API para provedores de IA

Exemplo de uso:
    >>> from pyflow.core.config import settings
    >>> print(settings.PYFLOW_HOST)
    '127.0.0.1'
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """
    Classe de configurações do PyFlow.

    Utiliza Pydantic Settings para carregar configurações de variáveis
    de ambiente e arquivo .env automaticamente.

    Attributes:
        PYFLOW_HOST: Endereço do host para o servidor (padrão: 127.0.0.1).
        PYFLOW_DEFAULT_PORT: Porta padrão do servidor (padrão: 8000).
        PYFLOW_PORT_SEARCH_MAX_TRIES: Máximo de tentativas para encontrar porta livre.
        PYFLOW_DEFAULT_TIMEOUT_SECONDS: Timeout padrão para execução de código.
        PYFLOW_MAX_CODE_CHARS: Limite máximo de caracteres do código.
        PYFLOW_MAX_OUTPUT_CHARS_DEFAULT: Limite padrão de saída.
        PYFLOW_MAX_OUTPUT_CHARS_MAX: Limite máximo absoluto de saída.
        PYFLOW_AI_MAX_TOKENS: Máximo de tokens para respostas da IA.
        PYFLOW_AI_TEMPERATURE: Temperatura para geração da IA.
        OPENROUTER_API_KEY: Chave de API do OpenRouter (opcional).
        OPENAI_API_KEY: Chave de API da OpenAI (opcional).
        GEMINI_API_KEY: Chave de API do Google Gemini (opcional).
        ANTHROPIC_API_KEY: Chave de API da Anthropic (opcional).
        DEEPSEEK_API_KEY: Chave de API do DeepSeek (opcional).
    """

    # Rede / Servidor
    PYFLOW_HOST: str = "127.0.0.1"
    PYFLOW_DEFAULT_PORT: int = 8000
    PYFLOW_PORT_SEARCH_MAX_TRIES: int = 50

    # Execução
    PYFLOW_DEFAULT_TIMEOUT_SECONDS: int = 30
    PYFLOW_MAX_CODE_CHARS: int = 100_000
    PYFLOW_MAX_OUTPUT_CHARS_DEFAULT: int = 100_000
    PYFLOW_MAX_OUTPUT_CHARS_MAX: int = 500_000

    # IA
    PYFLOW_AI_MAX_TOKENS: int = 800
    PYFLOW_AI_TEMPERATURE: float = 1.0

    # Chaves de API (Fallbacks)
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None

    # Segurança
    PYFLOW_API_TOKEN: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Shared filesystem locations (kept here to avoid circular imports between
# pyflow.core.connection and pyflow.core.security).
CONNECTION_DIR = Path.home() / ".pyflow"
CONNECTION_FILE = CONNECTION_DIR / "connection.json"
