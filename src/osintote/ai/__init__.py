# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""AI module — provider abstraction, query engine, workflow suggestions.

Provides a unified interface for AI-powered OSINT analysis:

- ``ai.provider`` — AI provider abstraction (OpenAI-compatible HTTP base)
- ``ai.query_engine`` — Natural-language → DSL → SQL pipeline
- ``ai.suggester`` — Post-task recommendation engine

Usage::

    from osintote.ai.provider import AIProviderRegistry

    registry = AIProviderRegistry()
    response = await registry.analyze("Find all critical vulnerabilities")
"""

from __future__ import annotations

from osintote.ai.analysis_engine import AnalysisEngine, AnalysisResult
from osintote.ai.models import (
    AIProviderType,
    ChatMessage,
    ChatMessageRole,
    ModelInfo,
)
from osintote.ai.provider import AIProvider, AIProviderRegistry, OpenAICompatibleHTTP
from osintote.ai.query_engine import QueryEngine
from osintote.ai.suggester import FindingSuggestion, Suggester

__all__: list[str] = [
    "AIProvider",
    "AIProviderRegistry",
    "AIProviderType",
    "AnalysisEngine",
    "AnalysisResult",
    "ChatMessage",
    "ChatMessageRole",
    "FindingSuggestion",
    "ModelInfo",
    "OpenAICompatibleHTTP",
    "QueryEngine",
    "Suggester",
]
