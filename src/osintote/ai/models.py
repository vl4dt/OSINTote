# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""AI provider models — typed data classes for LLM interactions.

Provides:
    - ChatMessage with role-based typing
    - ModelInfo for auto-discovery
    - AIProviderType enum for supported providers
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ChatMessageRole(str, Enum):
    """Chat message role (OpenAI API compatible)."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """A single chat message.

    Attributes
    ----------
    role:
        Message role (system/user/assistant).
    content:
        Text content of the message.
    """

    role: ChatMessageRole
    content: str


class ModelInfo(BaseModel):
    """Information about a discovered model.

    Attributes
    ----------
    id:
        Model identifier (e.g., "llama3", "gpt-4o").
    object:
        Object type (usually "model").
    owned_by:
        Provider/organization that owns the model.
    """

    id: str
    object: str = "model"
    owned_by: str = ""


class AIProviderType(str, Enum):
    """Supported AI provider types."""

    OPENAI = "openai"
    OLLAMA = "ollama"
    LLMSTUDIO = "lmstudio"
    LLAMACPP = "llamacpp"
    VLLM = "vllm"
    CUSTOM = "custom"

    @property
    def base_url(self) -> str:
        """Default base URL for this provider type."""
        defaults = {
            AIProviderType.OPENAI: "https://api.openai.com/v1",
            AIProviderType.OLLAMA: "http://localhost:11434/v1",
            AIProviderType.LLMSTUDIO: "http://localhost:1234/v1",
            AIProviderType.LLAMACPP: "http://localhost:8080/v1",
            AIProviderType.VLLM: "http://localhost:8000/v1",
            AIProviderType.CUSTOM: "",
        }
        return defaults[self]

    @property
    def default_model(self) -> str:
        """Default model name for this provider type."""
        defaults = {
            AIProviderType.OPENAI: "gpt-4o",
            AIProviderType.OLLAMA: "llama3",
            AIProviderType.LLMSTUDIO: "llama3",
            AIProviderType.LLAMACPP: "llama3",
            AIProviderType.VLLM: "llama3",
            AIProviderType.CUSTOM: "",
        }
        return defaults[self]


class AISummary(BaseModel):
    """Structured AI summary of OSINT findings.

    Attributes
    ----------
    risk_score:
        Numeric risk score (0.0 — 10.0).
    summary:
        Executive summary of findings.
    findings:
        Array of structured findings.
    recommendations:
        Actionable recommendations.
    missing_data:
        Gaps in intelligence that limit analysis.
    """

    risk_score: float = Field(
        ge=0.0,
        le=10.0,
        default=0.0,
        description="Numeric risk score (0.0 = low, 10.0 = critical).",
    )
    summary: str = Field(
        default="",
        description="Executive summary of findings.",
    )
    findings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Structured findings with severity, evidence, and recommendation.",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations.",
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="Gaps in intelligence.",
    )


class AIAnalysisResult(BaseModel):
    """Result of an AI analysis call.

    Attributes
    ----------
    summary:
        Structured AI summary.
    raw:
        Raw response content (for debugging).
    model_used:
        Model identifier that was used.
    """

    summary: AISummary
    raw: str = ""
    model_used: str = ""
