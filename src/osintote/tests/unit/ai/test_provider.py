# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for AI provider abstraction."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from osintote.ai.models import (
    AIProviderType,
    ChatMessage,
    ChatMessageRole,
    ModelInfo,
)
from osintote.ai.provider import (
    AIProviderRegistry,
    LlamaCPPProvider,
    LMStudioProvider,
    OpenAICompatibleHTTP,
    OpenAIProvider,
    OllamaProvider,
    VLLMProvider,
)
from osintote.engine.config import AIClientConfig


class TestAIProviderType:
    """Tests for AIProviderType enum."""

    def test_openai_defaults(self) -> None:
        p = AIProviderType.OPENAI
        assert p.base_url == "https://api.openai.com/v1"
        assert p.default_model == "gpt-4o"

    def test_ollama_defaults(self) -> None:
        p = AIProviderType.OLLAMA
        assert p.base_url == "http://localhost:11434/v1"
        assert p.default_model == "llama3"

    def test_custom_no_defaults(self) -> None:
        p = AIProviderType.CUSTOM
        assert p.base_url == ""
        assert p.default_model == ""


class TestChatMessage:
    """Tests for ChatMessage model."""

    def test_create_system_message(self) -> None:
        msg = ChatMessage(role=ChatMessageRole.SYSTEM, content="test")
        assert msg.role == ChatMessageRole.SYSTEM
        assert msg.content == "test"

    def test_create_user_message(self) -> None:
        msg = ChatMessage(role=ChatMessageRole.USER, content="query")
        assert msg.role == ChatMessageRole.USER

    def test_create_assistant_message(self) -> None:
        msg = ChatMessage(role=ChatMessageRole.ASSISTANT, content="response")
        assert msg.role == ChatMessageRole.ASSISTANT

    def test_to_dict(self) -> None:
        msg = ChatMessage(role=ChatMessageRole.USER, content="test")
        d = msg.model_dump()
        assert d["role"] == "user"
        assert d["content"] == "test"


class TestModelInfo:
    """Tests for ModelInfo model."""

    def test_create(self) -> None:
        m = ModelInfo(id="llama3", owned_by="ollama")
        assert m.id == "llama3"
        assert m.object == "model"
        assert m.owned_by == "ollama"


class TestOpenAICompatibleHTTP:
    """Tests for OpenAICompatibleHTTP base provider."""

    def test_init_defaults(self) -> None:
        provider = OpenAICompatibleHTTP()
        assert provider.base_url == "http://localhost:11434/v1"
        assert provider.model == "llama3"
        assert provider.max_tokens == 4096
        assert provider.temperature == 0.3

    def test_custom_init(self) -> None:
        provider = OpenAICompatibleHTTP(
            base_url="http://example.com/v1",
            model="gpt-4",
            max_tokens=8192,
            temperature=0.7,
        )
        assert provider.base_url == "http://example.com/v1"
        assert provider.model == "gpt-4"
        assert provider.max_tokens == 8192
        assert provider.temperature == 0.7

    @pytest.mark.asyncio
    async def test_parse_json_direct(self) -> None:
        provider = OpenAICompatibleHTTP()
        raw = '{"risk_score": 7.5, "summary": "Test"}'
        result = provider._parse_json(raw)
        assert result["risk_score"] == 7.5
        assert result["summary"] == "Test"

    @pytest.mark.asyncio
    async def test_parse_json_markdown_wrapped(self) -> None:
        provider = OpenAICompatibleHTTP()
        raw = "```json\n{\"risk_score\": 3.0, \"summary\": \"Low risk\"}\n```"
        result = provider._parse_json(raw)
        assert result["risk_score"] == 3.0
        assert result["summary"] == "Low risk"

    @pytest.mark.asyncio
    async def test_parse_json_fallback_to_raw(self) -> None:
        provider = OpenAICompatibleHTTP()
        raw = "This is just text, not JSON at all"
        result = provider._parse_json(raw)
        assert result == {"raw": raw}

    @pytest.mark.asyncio
    async def test_parse_suggestions_numbered(self) -> None:
        provider = OpenAICompatibleHTTP()
        raw = "1. Check for default credentials\n2. Run nmap scan\n3. Verify firewall rules"
        suggestions = provider._parse_suggestions(raw)
        assert len(suggestions) == 3
        assert "Check for default credentials" in suggestions[0]
        assert "Run nmap scan" in suggestions[1]
        assert "Verify firewall rules" in suggestions[2]

    @pytest.mark.asyncio
    async def test_parse_suggestions_parenthesized(self) -> None:
        provider = OpenAICompatibleHTTP()
        raw = "(1) Investigate further\n(2) Document findings"
        suggestions = provider._parse_suggestions(raw)
        assert len(suggestions) == 2

    @pytest.mark.asyncio
    async def test_parse_suggestions_continuation(self) -> None:
        provider = OpenAICompatibleHTTP()
        raw = "1. First recommendation\n   with continuation\n2. Second"
        suggestions = provider._parse_suggestions(raw)
        assert "with continuation" in suggestions[0]

    @pytest.mark.asyncio
    async def test_parse_suggestions_non_numbered_fallback(self) -> None:
        provider = OpenAICompatibleHTTP()
        raw = "Just a plain suggestion"
        suggestions = provider._parse_suggestions(raw)
        assert suggestions == ["Just a plain suggestion"]


class TestProviderClasses:
    """Tests for provider-specific subclasses."""

    def test_ollama_defaults(self) -> None:
        p = OllamaProvider()
        assert p.base_url == "http://localhost:11434/v1"
        assert p.model == "llama3"

    def test_lmstudio_defaults(self) -> None:
        p = LMStudioProvider()
        assert p.base_url == "http://localhost:1234/v1"
        assert p.model == "llama3"

    def test_llamacpp_defaults(self) -> None:
        p = LlamaCPPProvider()
        assert p.base_url == "http://localhost:8080/v1"
        assert p.model == "llama3"

    def test_vllm_defaults(self) -> None:
        p = VLLMProvider()
        assert p.base_url == "http://localhost:8000/v1"
        assert p.model == "llama3"

    def test_openai_defaults(self) -> None:
        p = OpenAIProvider()
        assert p.base_url == "https://api.openai.com/v1"
        assert p.model == "gpt-4o"


class TestAIProviderRegistry:
    """Tests for AIProviderRegistry."""

    def test_disabled_registry(self) -> None:
        config = AIClientConfig(enabled=False)
        registry = AIProviderRegistry(config)
        assert registry.is_enabled is False
        assert registry._get_provider() is None

    def test_enabled_registry_creates_provider(self) -> None:
        config = AIClientConfig(
            enabled=True,
            provider="ollama",
            base_url="http://localhost:11434/v1",
            model="llama3",
        )
        registry = AIProviderRegistry(config)
        assert registry.is_enabled is True
        provider = registry._get_provider()
        assert provider is not None
        assert isinstance(provider, OllamaProvider)

    def test_registry_from_config(self) -> None:
        config = AIClientConfig(
            enabled=True,
            provider="openai",
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
        )
        registry = AIProviderRegistry.from_config(config)
        assert registry.is_enabled is True
        provider = registry._get_provider()
        assert isinstance(provider, OpenAIProvider)

    @pytest.mark.asyncio
    async def test_disabled_registry_analyze_returns_error(self) -> None:
        config = AIClientConfig(enabled=False)
        registry = AIProviderRegistry(config)
        result = await registry.analyze("test prompt")
        assert "error" in result
        assert "disabled" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_disabled_registry_query_returns_empty(self) -> None:
        config = AIClientConfig(enabled=False)
        registry = AIProviderRegistry(config)
        result = await registry.query("test query")
        assert result == ""

    @pytest.mark.asyncio
    async def test_disabled_registry_suggest_returns_empty(self) -> None:
        config = AIClientConfig(enabled=False)
        registry = AIProviderRegistry(config)
        result = await registry.suggest("context", "target")
        assert result == []

    @pytest.mark.asyncio
    async def test_disabled_registry_list_models_returns_empty(self) -> None:
        config = AIClientConfig(enabled=False)
        registry = AIProviderRegistry(config)
        result = await registry.list_models()
        assert result == []

    @pytest.mark.asyncio
    async def test_disabled_registry_is_available(self) -> None:
        config = AIClientConfig(enabled=False)
        registry = AIProviderRegistry(config)
        result = await registry.is_available()
        assert result is False

    def test_custom_provider_type(self) -> None:
        config = AIClientConfig(
            enabled=True,
            provider="custom",
            base_url="http://example.com/v1",
            model="my-model",
        )
        registry = AIProviderRegistry(config)
        provider = registry._get_provider()
        assert isinstance(provider, OpenAICompatibleHTTP)
        assert provider.base_url == "http://example.com/v1"
        assert provider.model == "my-model"

    def test_vllm_provider_type(self) -> None:
        config = AIClientConfig(
            enabled=True,
            provider="vllm",
        )
        registry = AIProviderRegistry(config)
        provider = registry._get_provider()
        assert isinstance(provider, VLLMProvider)

    def test_llamacpp_provider_type(self) -> None:
        config = AIClientConfig(
            enabled=True,
            provider="llamacpp",
        )
        registry = AIProviderRegistry(config)
        provider = registry._get_provider()
        assert isinstance(provider, LlamaCPPProvider)
