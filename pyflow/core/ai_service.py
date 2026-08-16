"""
Serviço de integração com IA do PyFlow.

Este módulo fornece a classe AIService que gerencia todas as
interações com provedores de IA (OpenAI, Gemini, Anthropic, etc)
através da biblioteca LiteLLM.

Funcionalidades principais:
    - Explicação automática de erros de código
    - Chat contextual com código do usuário
    - Suporte a múltiplos provedores de IA
    - Suporte especial para GPT-5 via Responses API
    - Formatação de código com números de linha para contexto

A classe AIService é totalmente estática e não mantém estado,
facilitando o uso assíncrono em múltiplas requisições.
"""

import json
import re
import httpx
from typing import Optional, List, Dict
from litellm import acompletion
from tenacity import retry, stop_after_attempt, wait_fixed
from loguru import logger

from pyflow.core.models import AIConfig, AIErrorHelp, ChatMessage, Diagnostics
from pyflow.core.config import settings


class AIService:
    """
    Serviço para interações com provedores de IA.

    Fornece métodos estáticos para explicação de erros e chat
    contextual, com suporte a múltiplos provedores via LiteLLM
    e suporte especial para modelos GPT-5.

    Methods:
        explain_error: Gera explicação de IA para um erro de código.
        chat: Processa uma mensagem de chat com contexto de código.
    """

    @staticmethod
    def _is_gpt5_model(model_id: str) -> bool:
        """
        Verifica se o modelo é da família GPT-5 que requer Responses API.

        Args:
            model_id: Identificador do modelo.

        Returns:
            bool: True se for um modelo GPT-5.
        """
        model_lower = model_id.lower()
        return "gpt-5" in model_lower

    @staticmethod
    def _supports_json_mode(model: str) -> bool:
        """
        Verifica se o modelo suporta response_format json_object.

        Alguns provedores (DeepSeek, Ollama) rejeitam o parâmetro
        response_format; para eles a chamada é feita sem esse parâmetro.

        Args:
            model: Identificador do modelo.

        Returns:
            bool: True se o modelo suporta response_format json_object.
        """
        lowered = model.lower()
        return "deepseek" not in lowered and "ollama" not in lowered

    @staticmethod
    def _is_openrouter(config: AIConfig) -> bool:
        """
        Verifica se a configuração usa OpenRouter.

        OpenRouter é identificado pelo provider 'openrouter' ou
        pela base_url contendo 'openrouter.ai'.

        Args:
            config: Configuração do provedor de IA.

        Returns:
            bool: True se for OpenRouter.
        """
        if config.provider.lower() == "openrouter":
            return True
        if config.base_url and "openrouter.ai" in config.base_url.lower():
            return True
        return False

    @staticmethod
    def _build_model_string(config: AIConfig) -> str:
        """
        Constrói a string de modelo para LiteLLM.

        Padroniza o formato provider/model_id para uso com LiteLLM,
        tratando casos especiais como modelos OpenAI GPT e OpenRouter.

        Args:
            config: Configuração do provedor de IA.

        Returns:
            str: String formatada para LiteLLM (ex: 'openai/gpt-4').
        """
        # Regra 9.2: padronizar provider/model_id
        if "/" in config.model_id:
            # Assumindo que o usuário já mandou "provider/model"
            return config.model_id

        # OpenRouter: usar o model_id diretamente (já inclui provider/model)
        # OpenRouter espera formatos como "openai/gpt-4o", "anthropic/claude-3"
        if config.provider.lower() == "openrouter":
            return config.model_id

        # Para modelos OpenAI GPT, passar diretamente sem prefixo
        # LiteLLM reconhece gpt-* automaticamente
        if config.model_id.lower().startswith("gpt-"):
            return config.model_id

        # Google/Gemini: LiteLLM expects "gemini/" prefix for models like "gemini-pro"
        # The user UI sends provider="google"
        if config.provider.lower() == "google":
            # Avoid double prefixing if user typed "gemini/..."
            if "/" in config.model_id:
                return config.model_id
            return f"gemini/{config.model_id}"

        # Caso especial OpenAI: litellm aceita "gpt-4" direto, mas "openai/gpt-4" também funciona.
        # Vamos prefixar sempre para clareza, exceto se provider for "custom" ou algo assim.
        return f"{config.provider}/{config.model_id}"

    @staticmethod
    def _format_code_with_lines(code: str) -> str:
        """
        Formata código com números de linha para melhor contexto da IA.

        Adiciona números de linha formatados (ex: '001 | código')
        para ajudar a IA a referenciar linhas específicas.

        Args:
            code: Código Python original.

        Returns:
            str: Código formatado com números de linha.
        """
        if not code:
            return ""
        lines = code.splitlines()
        # Format: 001 | code line
        return "\n".join([f"{i+1:03d} | {line}" for i, line in enumerate(lines)])

    @classmethod
    def _get_openrouter_base_url(cls) -> str:
        """
        Retorna a URL base do OpenRouter.

        Returns:
            str: URL base da API do OpenRouter.
        """
        return "https://openrouter.ai/api/v1"

    @classmethod
    def _get_openrouter_headers(cls) -> Dict[str, str]:
        """
        Retorna headers extras para OpenRouter.

        OpenRouter aceita headers opcionais para identificação:
        - HTTP-Referer: URL do site para rankings
        - X-Title: Nome do site para rankings

        Returns:
            Dict[str, str]: Headers extras para a requisição.
        """
        return {
            "HTTP-Referer": "https://pyflow.local",
            "X-Title": "PyFlow"
        }

    @classmethod
    async def _call_gpt5_responses_api(
        cls,
        model: str,
        input_text: str,
        api_key: str,
        base_url: Optional[str] = None
    ) -> str:
        """
        Chama a API Responses da OpenAI para modelos GPT-5.

        Modelos GPT-5 requerem a API Responses em vez de Chat Completions.
        Este método utiliza o SDK oficial da OpenAI para fazer a chamada.

        Args:
            model: Identificador do modelo GPT-5.
            input_text: Texto de entrada para o modelo.
            api_key: Chave de API da OpenAI.
            base_url: URL base personalizada (opcional).

        Returns:
            str: Texto de resposta gerado pelo modelo.

        Raises:
            Exception: Se ocorrer erro na chamada da API.

        Note:
            Utiliza esforço de raciocínio 'minimal' para melhor latência.
        """
        from openai import OpenAI
        import asyncio
        
        # Create client with API key and base_url
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        logger.debug(f"GPT-5 API Request - Model: {model}")
        
        try:
            # Use responses.create for GPT-5 models
            # Run in executor since OpenAI SDK is sync
            # Note: gpt-5-nano supports 'minimal', 'low', 'medium', 'high' (not 'none')
            # gpt-5.2 supports 'none' but smaller models don't
            reasoning_effort = "minimal"  # Use lowest available for best latency
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.responses.create(
                    model=model,
                    input=input_text,
                    reasoning={"effort": reasoning_effort}
                )
            )
            
            logger.debug(f"GPT-5 API Response received")
            
            # Extract text from response
            # The response has an output_text attribute or output array
            if hasattr(response, 'output_text') and response.output_text:
                return response.output_text
            
            if hasattr(response, 'output') and response.output:
                for item in response.output:
                    if hasattr(item, 'type') and item.type == 'message':
                        if hasattr(item, 'content'):
                            for content in item.content:
                                if hasattr(content, 'type') and content.type == 'output_text':
                                    return content.text if hasattr(content, 'text') else str(content)
                                if hasattr(content, 'type') and content.type == 'text':
                                    return content.text if hasattr(content, 'text') else str(content)
            
            # Last resort: convert full response to string
            logger.warning(f"Unexpected GPT-5 response structure: {response}")
            return str(response)
            
        except Exception as e:
            logger.error(f"GPT-5 API Error: {e}")
            raise

    @classmethod
    async def _completion(
        cls,
        model: str,
        messages: list[dict],
        config: AIConfig,
        *,
        extra_headers: dict | None = None,
        response_format: dict | None = None,
        gpt5_input: str | None = None,
    ) -> str:
        """
        Route a completion through the GPT-5 Responses API or LiteLLM.

        GPT-5 models require the OpenAI Responses API, so `gpt5_input`
        (a plain-text prompt assembled by the caller) is sent to
        `_call_gpt5_responses_api`. All other models go through
        LiteLLM's `acompletion` with `messages`.

        The GPT-5 text building stays in each caller (`explain_error`,
        `chat`) to preserve the exact prompt shape each one historically
        built; `_completion` only decides which backend to use.

        Args:
            model: Model identifier for the provider.
            messages: Chat messages for the LiteLLM path.
            config: Provider configuration (api_key, base_url).
            extra_headers: Extra headers for the LiteLLM request.
            response_format: Response format for the LiteLLM request.
            gpt5_input: Plain-text input for the GPT-5 Responses API.

        Returns:
            str: The model's text response.
        """
        if cls._is_gpt5_model(model):
            base_url = config.base_url
            if cls._is_openrouter(config):
                base_url = config.base_url or cls._get_openrouter_base_url()
            return await cls._call_gpt5_responses_api(
                model=model,
                input_text=gpt5_input,
                api_key=config.api_key,
                base_url=base_url,
            )

        base_url = config.base_url
        if cls._is_openrouter(config):
            base_url = config.base_url or cls._get_openrouter_base_url()
            extra_headers = cls._get_openrouter_headers()

        params = {
            "model": model,
            "messages": messages,
            "api_key": config.api_key,
            "base_url": base_url,
            "max_tokens": settings.PYFLOW_AI_MAX_TOKENS,
            "temperature": settings.PYFLOW_AI_TEMPERATURE,
        }

        # Force usage of OpenAI client protocol for OpenRouter to respect
        # the base_url regardless of model prefix (e.g. anthropic/...)
        if cls._is_openrouter(config):
            params["custom_llm_provider"] = "openai"

        if extra_headers:
            params["extra_headers"] = extra_headers

        # Some providers (DeepSeek, Ollama) reject response_format, so only
        # send it to models that support json_object mode.
        supports_json_mode = cls._supports_json_mode(model)
        if response_format and supports_json_mode:
            params["response_format"] = response_format

        try:
            response = await acompletion(**params)
        except Exception:
            # A provider that nominally supports json mode can still reject
            # response_format; retry once without it.
            if response_format and supports_json_mode:
                logger.warning(
                    f"Model {model} rejected response_format; retrying without it"
                )
                params.pop("response_format", None)
                response = await acompletion(**params)
            else:
                raise

        return response.choices[0].message.content

    @classmethod
    async def explain_error(cls, code: str, stderr: str, diagnostics: Diagnostics, config: AIConfig) -> Optional[AIErrorHelp]:
        """
        Gera uma explicação de IA para um erro de execução de código.

        Utiliza o modelo de IA configurado para analisar o código e o erro,
        gerando um resumo compreensível, sugestão de correção e opcionalmente
        código corrigido.

        Args:
            code: Código Python que gerou o erro.
            stderr: Saída de erro completa do processo.
            diagnostics: Informações estruturadas do erro.
            config: Configuração do provedor de IA.

        Returns:
            AIErrorHelp: Objeto com resumo, correção sugerida e código.
            None: Se ocorrer erro na chamada da IA.

        Note:
            A resposta é solicitada em formato JSON para facilitar o parsing.
            O código é formatado com números de linha para contexto.
        """
        model = cls._build_model_string(config)
        
        system_prompt = settings.PYFLOW_AI_EXPLAINER_PROMPT
        
        formatted_code = cls._format_code_with_lines(code)
        
        user_content = f"""
Código do usuário (com números de linha):
```text
{formatted_code}
```

Erro Encontrado:
Tipo: {diagnostics.error_type}
Mensagem: {diagnostics.message}
Linha (estimada): {diagnostics.line}
Contexto:
{diagnostics.context or "N/A"}

Stderr completo:
{stderr}

Por favor, forneça o diagnóstico JSON.
"""
        
        try:
            # GPT-5 needs the system + user text concatenated exactly as
            # before; _completion decides which backend to use.
            full_input = f"{system_prompt}\n\n{user_content}"
            content = await cls._completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                config=config,
                response_format={"type": "json_object"},
                gpt5_input=full_input,
            )
            
            # Try to parse JSON, handling both clean JSON and markdown-wrapped JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code block
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(1))
                else:
                    # Last resort: try to find any JSON object
                    json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(0))
                    else:
                        data = {"summary": content, "probable_fix": "Veja a resposta acima."}
            
            return AIErrorHelp(
                summary=data.get("summary", "Não foi possível resumir."),
                probable_fix=data.get("probable_fix", "Sem sugestão de correção."),
                suggested_code=data.get("suggested_code")
            )

        except Exception as e:
            logger.error(f"Falha na IA (explain_error): {e}")
            return None

    @classmethod
    async def chat(cls, code: Optional[str], user_message: str, history: List[ChatMessage], config: AIConfig) -> str:
        """
        Processa uma mensagem de chat com contexto de código.

        Envia a mensagem do usuário para o modelo de IA junto com
        o código atual (se fornecido) e o histórico de conversa,
        retornando a resposta do assistente.

        Args:
            code: Código Python atual no editor para contexto (opcional).
            user_message: Mensagem do usuário.
            history: Histórico de mensagens anteriores.
            config: Configuração do provedor de IA.

        Returns:
            str: Resposta do modelo de IA formatada em Markdown.

        Note:
            O código é formatado com números de linha para referência.
            A resposta é formatada em Markdown para melhor legibilidade.
        """
        model = cls._build_model_string(config)

        system_prompt = settings.PYFLOW_AI_TUTOR_PROMPT
        
        # Build messages and the plain-text input for the GPT-5 path.
        # The caller keeps building gpt5_input so the exact prompt shape
        # each model historically received is preserved.
        messages = [{"role": "system", "content": system_prompt}]
        input_parts = [system_prompt]

        # Adicionar contexto do código se existir
        if code:
            formatted_code = cls._format_code_with_lines(code)
            messages.append({"role": "system", "content": f"Contexto do código atual (com linhas):\n```text\n{formatted_code}\n```"})
            input_parts.append(f"\nContexto do código atual (com linhas):\n```text\n{formatted_code}\n```")

        # Histórico
        for msg in history:
            messages.append(msg.model_dump())
            role_label = "Usuário" if msg.role == "user" else "Assistente"
            input_parts.append(f"\n{role_label}: {msg.content}")

        messages.append({"role": "user", "content": user_message})
        input_parts.append(f"\nUsuário: {user_message}")

        gpt5_input = "\n".join(input_parts) if cls._is_gpt5_model(model) else None

        try:
            return await cls._completion(
                model=model,
                messages=messages,
                config=config,
                gpt5_input=gpt5_input,
            )
        except Exception as e:
            error_label = "Falha na IA GPT-5 (chat)" if gpt5_input else "Falha na IA (chat)"
            logger.error(f"{error_label}: {e}")
            return f"Erro ao contatar IA: {str(e)}"

    @classmethod
    async def socratic_hint(cls, code: str, diagnostics: Diagnostics | None, level: int, config: AIConfig) -> str:
        """
        Gera uma dica socrática progressiva para o código do usuário.

        Utiliza o modelo de IA configurado para guiar o aluno na
        descoberta do erro em três níveis de profundidade:

        - Nível 1: pergunta-guia conceitual, sem fornecer a solução.
        - Nível 2: localiza a área problemática e o conceito envolvido.
        - Nível 3: quase-solução, apontando a causa exata e um esboço.

        Args:
            code: Código Python atual no editor.
            diagnostics: Informações estruturadas do erro (opcional).
            level: Nível da dica (1 a 3).
            config: Configuração do provedor de IA.

        Returns:
            str: Dica da IA formatada em Markdown.

        Note:
            O código é formatado com números de linha para referência.
            O prompt muda conforme o nível para escapar da resposta direta.
        """
        model = cls._build_model_string(config)
        level = max(1, min(3, level))

        level_instructions = {
            1: (
                "Nível 1: faça apenas uma pergunta-guia conceitual que leve o aluno "
                "a descobrir sozinho onde está o problema. NÃO forneça a solução e "
                "NÃO mencione a linha do erro."
            ),
            2: (
                "Nível 2: localize a área problemática indicando a linha aproximada "
                "e o conceito envolvido, mas sem dar a correção pronta."
            ),
            3: (
                "Nível 3: dê uma quase-solução: aponte a causa exata e ofereça um "
                "esboço ou pseudocódigo, incentivando o aluno a completar."
            ),
        }

        system_prompt = (
            "Você é um tutor socrático de Python para um adulto iniciante. "
            "Responda em português, usando Markdown curto.\n\n"
            f"Instrução desta resposta: {level_instructions[level]}"
        )

        formatted_code = cls._format_code_with_lines(code)

        user_content = f"""Código do usuário (com números de linha):
```text
{formatted_code}
```
"""

        if diagnostics:
            user_content += f"""
Diagnóstico do erro:
Tipo: {diagnostics.error_type}
Mensagem: {diagnostics.message}
Linha: {diagnostics.line}
Contexto: {diagnostics.context or "N/A"}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        gpt5_input = f"{system_prompt}\n\n{user_content}" if cls._is_gpt5_model(model) else None

        try:
            return await cls._completion(
                model=model,
                messages=messages,
                config=config,
                gpt5_input=gpt5_input,
            )
        except Exception as e:
            error_label = "Falha na IA GPT-5 (socratic_hint)" if gpt5_input else "Falha na IA (socratic_hint)"
            logger.error(f"{error_label}: {e}")
            return f"Erro ao contatar IA: {str(e)}"
