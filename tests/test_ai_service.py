"""AI service unit tests (no network calls)."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from pyflow.core.ai_service import AIService
from pyflow.core.models import AIConfig, ChatMessage


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
