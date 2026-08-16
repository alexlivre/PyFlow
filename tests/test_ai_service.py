"""AI service unit tests (no network calls)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from pyflow.core.ai_service import AIService
from pyflow.core.config import settings
from pyflow.core.models import AIConfig, ChatMessage, Diagnostics


def test_chat_message_rejects_invalid_role():
    with pytest.raises(ValidationError):
        ChatMessage(role="system", content="x")


def test_build_model_string_openrouter_passthrough():
    cfg = AIConfig(provider="openrouter", model_id="anthropic/claude-3.5-sonnet")
    assert AIService._build_model_string(cfg) == "anthropic/claude-3.5-sonnet"


def test_build_model_string_google_prefix():
    cfg = AIConfig(provider="google", model_id="gemini-2.5-flash")
    assert AIService._build_model_string(cfg) == "gemini/gemini-2.5-flash"


def test_build_model_string_gpt_passthrough():
    cfg = AIConfig(provider="openai", model_id="gpt-5-nano")
    assert AIService._build_model_string(cfg) == "gpt-5-nano"


def test_build_model_string_minimax_prefix():
    cfg = AIConfig(provider="minimax", model_id="MiniMax-M3")
    assert AIService._build_model_string(cfg) == "minimax/MiniMax-M3"


def test_build_model_string_opencode_passthrough():
    cfg = AIConfig(provider="opencode", model_id="deepseek-v4-flash")
    assert AIService._build_model_string(cfg) == "deepseek-v4-flash"


def test_build_model_string_opencode_go_passthrough():
    cfg = AIConfig(provider="opencode-go", model_id="gpt-5.6-luna")
    assert AIService._build_model_string(cfg) == "gpt-5.6-luna"


def test_opencode_endpoint_kind():
    assert AIService._opencode_endpoint_kind("gpt-5.6-luna") == "responses"
    assert AIService._opencode_endpoint_kind("claude-sonnet-4-5") == "messages"
    assert AIService._opencode_endpoint_kind("minimax-m3") == "messages"
    assert AIService._opencode_endpoint_kind("deepseek-v4-flash") == "chat"
    assert AIService._opencode_endpoint_kind("kimi-k3") == "chat"


def test_is_opencode_detection():
    assert AIService._is_opencode(AIConfig(provider="opencode", model_id="x")) is True
    assert AIService._is_opencode(AIConfig(provider="openai", model_id="x")) is False
    assert AIService._is_opencode_go(AIConfig(provider="opencode-go", model_id="x")) is True
    assert AIService._is_opencode_go(AIConfig(provider="opencode", model_id="x")) is False


def test_resolve_base_url_opencode_defaults():
    zen = AIService._resolve_base_url(AIConfig(provider="opencode", model_id="x"))
    assert zen == "https://opencode.ai/zen/v1"
    go = AIService._resolve_base_url(AIConfig(provider="opencode-go", model_id="x"))
    assert go == "https://opencode.ai/zen/go/v1"


def test_resolve_base_url_respects_user_override():
    cfg = AIConfig(provider="opencode", model_id="x", base_url="http://localhost:9999/v1")
    assert AIService._resolve_base_url(cfg) == "http://localhost:9999/v1"


def test_format_code_with_lines():
    out = AIService._format_code_with_lines("a\nb")
    assert out == "001 | a\n002 | b"


def test_gpt5_detection():
    assert AIService._is_gpt5_model("gpt-5-nano") is True
    assert AIService._is_gpt5_model("gpt-4o") is False


def test_completion_routes_gpt5_to_responses_api():
    cfg = AIConfig(provider="openai", model_id="gpt-5-nano", api_key="test-key")
    mock = AsyncMock(return_value="resposta do gpt-5")
    with patch.object(AIService, "_call_gpt5_responses_api", new=mock):
        result = asyncio.run(
            AIService._completion(
                model="gpt-5-nano",
                messages=[{"role": "user", "content": "oi"}],
                config=cfg,
                gpt5_input="System: ...\n\nUsuário: oi",
            )
        )
    assert result == "resposta do gpt-5"
    mock.assert_awaited_once_with(
        model="gpt-5-nano",
        input_text="System: ...\n\nUsuário: oi",
        api_key="test-key",
        base_url=None,
    )


def test_supports_json_mode():
    assert AIService._supports_json_mode("deepseek-chat") is False
    assert AIService._supports_json_mode("ollama/llama3") is False
    assert AIService._supports_json_mode("gpt-4o") is True


def test_completion_retries_without_response_format_when_rejected():
    cfg = AIConfig(provider="openai", model_id="gpt-4o", api_key="test-key")
    response = MagicMock()
    response.choices[0].message.content = "ok"
    mock = AsyncMock(side_effect=[Exception("response_format not supported"), response])
    with patch("pyflow.core.ai_service.acompletion", new=mock):
        result = asyncio.run(
            AIService._completion(
                model="gpt-4o",
                messages=[{"role": "user", "content": "oi"}],
                config=cfg,
                response_format={"type": "json_object"},
            )
        )
    assert result == "ok"
    assert mock.await_count == 2
    first_call = mock.await_args_list[0].kwargs
    second_call = mock.await_args_list[1].kwargs
    assert first_call["response_format"] == {"type": "json_object"}
    assert "response_format" not in second_call


def test_completion_omits_response_format_for_unsupported_models():
    cfg = AIConfig(provider="deepseek", model_id="deepseek-chat", api_key="test-key")
    response = MagicMock()
    response.choices[0].message.content = "ok"
    mock = AsyncMock(return_value=response)
    with patch("pyflow.core.ai_service.acompletion", new=mock):
        result = asyncio.run(
            AIService._completion(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "oi"}],
                config=cfg,
                response_format={"type": "json_object"},
            )
        )
    assert result == "ok"
    mock.assert_awaited_once()
    assert "response_format" not in mock.await_args.kwargs


def test_chat_uses_tutor_prompt_from_settings():
    cfg = AIConfig(provider="openai", model_id="gpt-4o", api_key="test-key")
    response = MagicMock()
    response.choices[0].message.content = "ok"
    mock = AsyncMock(return_value=response)
    with patch("pyflow.core.ai_service.acompletion", new=mock):
        result = asyncio.run(
            AIService.chat(
                code=None,
                user_message="oi",
                history=[],
                config=cfg,
            )
        )
    assert result == "ok"
    sent_messages = mock.await_args.kwargs["messages"]
    assert sent_messages[0] == {
        "role": "system",
        "content": settings.PYFLOW_AI_TUTOR_PROMPT,
    }

def test_socratic_hint_level1_asks_guiding_question_without_solution():
    cfg = AIConfig(provider="openai", model_id="gpt-4o", api_key="test-key")
    response = MagicMock()
    response.choices[0].message.content = "O que você acha que está errado?"
    mock = AsyncMock(return_value=response)
    with patch("pyflow.core.ai_service.acompletion", new=mock):
        result = asyncio.run(
            AIService.socratic_hint(
                code="x = 1\nprint(y)",
                diagnostics=None,
                level=1,
                config=cfg,
            )
        )
    assert result == "O que você acha que está errado?"
    system_prompt = mock.await_args.kwargs["messages"][0]["content"]
    assert "pergunta" in system_prompt
    assert "NÃO forneça a solução" in system_prompt


def test_socratic_hint_level3_includes_diagnostics_line():
    cfg = AIConfig(provider="openai", model_id="gpt-4o", api_key="test-key")
    response = MagicMock()
    response.choices[0].message.content = "Quase lá: confira a linha 2"
    mock = AsyncMock(return_value=response)
    diag = Diagnostics(
        error_type="NameError",
        message="name 'y' is not defined",
        line=2,
    )
    with patch("pyflow.core.ai_service.acompletion", new=mock):
        result = asyncio.run(
            AIService.socratic_hint(
                code="x = 1\nprint(y)",
                diagnostics=diag,
                level=3,
                config=cfg,
            )
        )
    assert result == "Quase lá: confira a linha 2"
    user_content = mock.await_args.kwargs["messages"][1]["content"]
    assert "NameError" in user_content
    assert "Linha" in user_content


def test_socratic_hint_level1_omits_diagnostics():
    cfg = AIConfig(provider="openai", model_id="gpt-4o", api_key="test-key")
    response = MagicMock()
    response.choices[0].message.content = "O que você acha que está errado?"
    mock = AsyncMock(return_value=response)
    diag = Diagnostics(
        error_type="ZeroDivisionError",
        message="division by zero",
        line=1,
    )
    with patch("pyflow.core.ai_service.acompletion", new=mock):
        result = asyncio.run(
            AIService.socratic_hint(
                code="x = 1/0",
                diagnostics=diag,
                level=1,
                config=cfg,
            )
        )
    assert result == "O que você acha que está errado?"
    user_content = mock.await_args.kwargs["messages"][1]["content"]
    assert "ZeroDivisionError" not in user_content
    assert "division by zero" not in user_content
    assert "Linha" not in user_content
    assert "não está funcionando como esperado" in user_content


def test_completion_opencode_messages_model_uses_anthropic_provider():
    cfg = AIConfig(provider="opencode", model_id="claude-sonnet-4-5", api_key="test-key")
    response = MagicMock()
    response.choices[0].message.content = "ok"
    mock = AsyncMock(return_value=response)
    with patch("pyflow.core.ai_service.acompletion", new=mock):
        result = asyncio.run(
            AIService._completion(
                model="claude-sonnet-4-5",
                messages=[{"role": "user", "content": "oi"}],
                config=cfg,
            )
        )
    assert result == "ok"
    kwargs = mock.await_args.kwargs
    assert kwargs["custom_llm_provider"] == "anthropic"
    assert kwargs["base_url"] == "https://opencode.ai/zen/v1"
    assert "extra_headers" not in kwargs


def test_completion_opencode_chat_model_uses_openai_provider():
    cfg = AIConfig(provider="opencode-go", model_id="deepseek-v4-flash", api_key="test-key")
    response = MagicMock()
    response.choices[0].message.content = "ok"
    mock = AsyncMock(return_value=response)
    with patch("pyflow.core.ai_service.acompletion", new=mock):
        result = asyncio.run(
            AIService._completion(
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": "oi"}],
                config=cfg,
            )
        )
    assert result == "ok"
    kwargs = mock.await_args.kwargs
    assert kwargs["custom_llm_provider"] == "openai"
    assert kwargs["base_url"] == "https://opencode.ai/zen/go/v1"
    assert "extra_headers" not in kwargs


def test_completion_opencode_gpt5_routes_to_responses_api():
    cfg = AIConfig(provider="opencode", model_id="gpt-5.6-luna", api_key="test-key")
    mock = AsyncMock(return_value="ok")
    with patch.object(AIService, "_call_gpt5_responses_api", new=mock):
        result = asyncio.run(
            AIService._completion(
                model="gpt-5.6-luna",
                messages=[{"role": "user", "content": "oi"}],
                config=cfg,
                gpt5_input="input",
            )
        )
    assert result == "ok"
    mock.assert_awaited_once_with(
        model="gpt-5.6-luna",
        input_text="input",
        api_key="test-key",
        base_url="https://opencode.ai/zen/v1",
    )
