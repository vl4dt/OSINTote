# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""AI provider abstraction — unified interface for LLM interactions.

Provides:
    - ``AIProvider`` abstract interface (analyze/query/suggest methods)
    - ``OpenAICompatibleHTTP`` base class (any OpenAI-compatible API)
    - Provider-specific extensions (Ollama, LMStudio, llama.cpp, vLLM)
    - ``AIProviderRegistry`` for auto-discovery and selection

Usage::

    from osintote.ai.provider import AIProviderRegistry
    from osintote.engine.config import EngineConfig

    config = EngineConfig.load()
    registry = AIProviderRegistry.from_config(config)
    result = await registry.analyze("Find all critical vulnerabilities")
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel, Field, SecretStr

from ..engine.config import AIClientConfig
from .models import (
    AIProviderType,
    ChatMessage,
    ChatMessageRole,
    ModelInfo,
)

logger = logging.getLogger(__name__)


# ── Abstract interface ──────────────────────────────────────────────────


class AIProvider(ABC):
    """Abstract base for all AI providers.

    Every provider must implement:
        - analyze(prompt, system_prompt) → AISummary
        - query(prompt) → str
        - suggest(context, target) → list[str]
    """

    @abstractmethod
    async def analyze(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run AI analysis on text input.

        Parameters
        ----------
        prompt:
            Input text to analyze.
        system_prompt:
            Optional system/instruction prompt.
        model:
            Optional model override.

        Returns
        -------
        dict
            Structured analysis result.
        """

    @abstractmethod
    async def query(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> str:
        """Run a conversational query.

        Parameters
        ----------
        prompt:
            User query text.
        system_prompt:
            Optional system/instruction prompt.
        model:
            Optional model override.

        Returns
        -------
        str
            AI-generated text response.
        """

    @abstractmethod
    async def suggest(
        self,
        context: str,
        target: str,
        model: str | None = None,
    ) -> list[str]:
        """Generate recommendations based on findings context.

        Parameters
        ----------
        context:
            Summarized OSINT findings.
        target:
            Target identifier.
        model:
            Optional model override.

        Returns
        -------
        list[str]
            List of recommendation strings.
        """

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """List available models from the provider.

        Returns
        -------
        list[ModelInfo]
            Available models.
        """

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is reachable.

        Returns
        -------
        bool
            True if the provider is online and responding.
        """


# ── OpenAI-compatible base class ────────────────────────────────────────


class OpenAICompatibleHTTP(AIProvider, BaseModel):
    """Base provider for any OpenAI-compatible HTTP API.

    Works with OpenAI, Ollama, LM Studio, llama.cpp, vLLM, and any
    service exposing an OpenAI-compatible chat completions endpoint.

    Parameters
    ----------
    base_url:
        API base URL (e.g., http://localhost:11434/v1).
    api_key:
        API key (optional for local providers).
    model:
        Default model name.
    max_tokens:
        Maximum tokens per response.
    temperature:
        Sampling temperature.
    timeout:
        Request timeout in seconds.
    """

    base_url: str = Field(default="http://localhost:11434/v1")
    api_key: SecretStr | None = Field(default=None)
    model: str = Field(default="llama3")
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    timeout: int = Field(default=120, ge=5)

    async def _client(self) -> httpx.AsyncClient:
        """Create an async HTTP client with configured headers."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key.get_secret_value()}"
        elif self.api_key is None:
            headers["Authorization"] = "Bearer no-key"

        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=httpx.Timeout(self.timeout),
        )

    async def analyze(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run AI analysis, attempting to parse JSON output."""
        system = system_prompt or (
            "You are an OSINT analyst. Return structured JSON responses."
        )
        messages = [
            ChatMessage(role=ChatMessageRole.SYSTEM, content=system),
            ChatMessage(role=ChatMessageRole.USER, content=prompt),
        ]
        raw = await self._chat(messages, model or self.model)
        return self._parse_json(raw)

    async def query(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> str:
        """Run a conversational query."""
        system = system_prompt or "You are a helpful OSINT analyst."
        messages = [
            ChatMessage(role=ChatMessageRole.SYSTEM, content=system),
            ChatMessage(role=ChatMessageRole.USER, content=prompt),
        ]
        return await self._chat(messages, model or self.model)

    async def suggest(
        self,
        context: str,
        target: str,
        model: str | None = None,
    ) -> list[str]:
        """Generate recommendations based on findings context."""
        system_prompt = (
            "You are an OSINT expert. Based on the findings below, "
            "provide a numbered list of specific follow-up investigation "
            "recommendations. Return ONLY the list, no extra text.\n\n"
            f"Target: {target}\n\nFindings:\n{context}"
        )
        raw = await self.query(system_prompt, model=model or self.model)
        return self._parse_suggestions(raw)

    async def list_models(self) -> list[ModelInfo]:
        """List available models via the /v1/models endpoint."""
        async with await self._client() as client:
            try:
                resp = await client.get("/models")
                resp.raise_for_status()
                data = resp.json()
                models = data.get("data", [])
                return [
                    ModelInfo(
                        id=m.get("id", ""),
                        object=m.get("object", "model"),
                        owned_by=m.get("owned_by", ""),
                    )
                    for m in models
                ]
            except Exception as exc:
                logger.warning("Failed to list models: %s", exc)
                return []

    async def is_available(self) -> bool:
        """Check if the provider is reachable."""
        async with await self._client() as client:
            try:
                await client.get("/models")
                return True
            except Exception:
                return False

    async def _chat(
        self,
        messages: list[ChatMessage],
        model: str,
    ) -> str:
        """Send a chat completion request and return the assistant response."""
        async with await self._client() as client:
            payload: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": m.role.value, "content": m.content}
                    for m in messages
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }
            resp = await client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            choice = data.get("choices", [{}])[0]
            return choice.get("message", {}).get("content", "")

    def _parse_json(self, raw: str) -> dict[str, Any]:
        """Extract JSON from an AI response (handles markdown wrapping)."""
        raw = raw.strip()
        # Try direct parse first
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # Try extracting from markdown code block
        start = raw.find("```")
        if start != -1:
            end = raw.rfind("```")
            if end > start:
                inner = raw[start + 3 : end].strip()
                inner = inner.replace("json", "").strip()
                try:
                    return json.loads(inner)
                except json.JSONDecodeError:
                    pass
        # Fallback: return raw text as a dict
        return {"raw": raw}

    def _parse_suggestions(self, raw: str) -> list[str]:
        """Parse numbered suggestions from AI text output."""
        lines = raw.strip().splitlines()
        suggestions: list[str] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            is_numbered = False
            # Match: "1. text", "1) text", or "(1) text"
            if len(line) > 0 and line[0].isdigit():
                after = line[1:4]
                if "." in after or ")" in after:
                    is_numbered = True
            elif len(line) > 2 and line[0] == "(" and line[1].isdigit() and line[2] == ")":
                is_numbered = True
            if is_numbered:
                idx = next((i for i, c in enumerate(line) if c.isdigit()), 0)
                rest = line[idx + 1:]
                sep = rest.find(".") if rest else -1
                if sep == -1:
                    sep = rest.find(")") if rest else -1
                if sep != -1:
                    suggestions.append(rest[sep + 1:].strip().lstrip(") "))
                else:
                    suggestions.append(line)
            elif suggestions:
                suggestions[-1] += " " + line
        return suggestions if suggestions else [raw.strip()]



    def model_dump(self) -> dict[str, Any]:
        """Serialize for config persistence."""
        data = self.model_dump(mode="python")
        if self.api_key:
            data["api_key"] = "****"
        return data


# ── Provider-specific extensions ────────────────────────────────────────


class OllamaProvider(OpenAICompatibleHTTP):
    """Ollama-specific provider with extended streaming support."""

    base_url: str = Field(default="http://localhost:11434/v1")
    model: str = Field(default="llama3")

    async def is_available(self) -> bool:
        """Check Ollama is available via both /models and /api/tags."""
        async with await self._client() as client:
            try:
                await client.get("/api/tags")
                return True
            except Exception:
                return False


class LMStudioProvider(OpenAICompatibleHTTP):
    """LM Studio provider configuration."""

    base_url: str = Field(default="http://localhost:1234/v1")
    model: str = Field(default="llama3")


class LlamaCPPProvider(OpenAICompatibleHTTP):
    """llama.cpp server provider configuration."""

    base_url: str = Field(default="http://localhost:8080/v1")
    model: str = Field(default="llama3")


class VLLMProvider(OpenAICompatibleHTTP):
    """vLLM provider configuration."""

    base_url: str = Field(default="http://localhost:8000/v1")
    model: str = Field(default="llama3")


class OpenAIProvider(OpenAICompatibleHTTP):
    """OpenAI provider configuration."""

    base_url: str = Field(default="https://api.openai.com/v1")
    model: str = Field(default="gpt-4o")


# ── Registry ────────────────────────────────────────────────────────────


class AIProviderRegistry:
    """Registry that selects the correct provider based on configuration.

    Creates the right provider instance from an ``AIClientConfig`` and
    caches it for reuse. Provides convenience methods that delegate to
    the resolved provider.

    Parameters
    ----------
    config:
        AI client configuration.
    """

    def __init__(self, config: AIClientConfig | None = None) -> None:
        self.config = config or AIClientConfig()
        self._provider: AIProvider | None = None

    @classmethod
    def from_config(cls, config: AIClientConfig | None = None) -> AIProviderRegistry:
        """Create a registry from configuration.

        Parameters
        ----------
        config:
            AI client configuration.

        Returns
        -------
        AIProviderRegistry
            A configured registry.
        """
        return cls(config)

    def _build_provider(self) -> AIProvider | None:
        """Instantiate the correct provider class from config."""
        if not self.config.enabled:
            return None

        provider_type = AIProviderType(self.config.provider)
        kwargs: dict[str, Any] = {
            "base_url": self.config.base_url,
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "timeout": self.config.timeout,
        }
        if self.config.api_key:
            kwargs["api_key"] = self.config.api_key

        providers: dict[AIProviderType, type[AIProvider]] = {
            AIProviderType.OPENAI: OpenAIProvider,
            AIProviderType.OLLAMA: OllamaProvider,
            AIProviderType.LLMSTUDIO: LMStudioProvider,
            AIProviderType.LLAMACPP: LlamaCPPProvider,
            AIProviderType.VLLM: VLLMProvider,
            AIProviderType.CUSTOM: OpenAICompatibleHTTP,
        }

        provider_cls = providers.get(provider_type, OpenAICompatibleHTTP)
        return provider_cls(**kwargs)

    def _get_provider(self) -> AIProvider | None:
        """Get or create the provider instance (lazy init + caching)."""
        if self._provider is None:
            self._provider = self._build_provider()
        return self._provider

    async def analyze(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run AI analysis using the configured provider.

        Parameters
        ----------
        prompt:
            Input text to analyze.
        system_prompt:
            Optional system/instruction prompt.
        model:
            Optional model override.

        Returns
        -------
        dict
            Structured analysis result, or error dict if unavailable.
        """
        provider = self._get_provider()
        if provider is None:
            return {"error": "AI is disabled in configuration"}
        try:
            return await provider.analyze(prompt, system_prompt, model)
        except Exception as exc:
            logger.error("AI analysis failed: %s", exc)
            return {"error": str(exc)}

    async def query(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> str:
        """Run a conversational query.

        Parameters
        ----------
        prompt:
            User query text.
        system_prompt:
            Optional system/instruction prompt.
        model:
            Optional model override.

        Returns
        -------
        str
            AI-generated response, or empty string on failure.
        """
        provider = self._get_provider()
        if provider is None:
            return ""
        try:
            return await provider.query(prompt, system_prompt, model)
        except Exception as exc:
            logger.error("AI query failed: %s", exc)
            return ""

    async def suggest(
        self,
        context: str,
        target: str,
        model: str | None = None,
    ) -> list[str]:
        """Generate recommendations based on findings context.

        Parameters
        ----------
        context:
            Summarized OSINT findings.
        target:
            Target identifier.
        model:
            Optional model override.

        Returns
        -------
        list[str]
            List of recommendation strings, or empty on failure.
        """
        provider = self._get_provider()
        if provider is None:
            return []
        try:
            return await provider.suggest(context, target, model)
        except Exception as exc:
            logger.error("AI suggestion failed: %s", exc)
            return []

    async def list_models(self) -> list[ModelInfo]:
        """List available models from the configured provider."""
        provider = self._get_provider()
        if provider is None:
            return []
        try:
            return await provider.list_models()
        except Exception as exc:
            logger.error("Model listing failed: %s", exc)
            return []

    async def is_available(self) -> bool:
        """Check if the configured provider is reachable."""
        provider = self._get_provider()
        if provider is None:
            return False
        try:
            return await provider.is_available()
        except Exception:
            return False

    @property
    def is_enabled(self) -> bool:
        """Whether AI is enabled in configuration."""
        return self.config.enabled
