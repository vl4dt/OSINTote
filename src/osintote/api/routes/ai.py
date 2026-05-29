# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""AI routes — natural-language query and analysis endpoints.

Endpoints:
    POST   /api/ai/query           — NL→DSL→SQL query
    POST   /api/ai/analyze         — Post-task AI analysis
    GET    /api/ai/models          — List available models
    GET    /api/ai/status          — Provider availability
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from osintote.ai.analysis_engine import AnalysisEngine, AnalysisResult
from osintote.ai.models import ModelInfo
from osintote.ai.provider import AIProviderRegistry
from osintote.ai.query_engine import DSLExecutor, DSLParser, NLFormatter
from osintote.models.database import get_async_session

router = APIRouter(prefix="/api/ai", tags=["ai"])

logger = logging.getLogger(__name__)


# ── Request/Response schemas ────────────────────────────────────────────


class QueryRequest(BaseModel):
    """Natural-language query request."""

    query: str
    use_ai: bool = True


class AnalyzeRequest(BaseModel):
    """Analysis request."""

    task_id: str
    target: str
    records: list[dict] = []
    task_type: str = ""


class ModelListResponse(BaseModel):
    """Model list response."""

    models: list[ModelInfo]
    available: bool


# ── Query engine (module-level singleton) ────────────────────────────────

# We lazily initialize the AI provider registry on first request
# to avoid blocking startup.
_ai_registry: AIProviderRegistry | None = None


def _get_registry() -> AIProviderRegistry | None:
    """Lazy-load the AI provider registry."""
    global _ai_registry
    if _ai_registry is None:
        from osintote.engine.config import EngineConfig

        config = EngineConfig.load()
        _ai_registry = AIProviderRegistry.from_config(config.ai)
    return _ai_registry


@router.post("/query")
async def execute_query(request: QueryRequest) -> dict:
    """Execute a natural-language query.

    Translates the query to DSL (via AI or rule-based parser) and
    returns formatted results.

    Parameters
    ----------
    request:
        QueryRequest with natural language query string.

    Returns
    -------
    dict:
        Formatted query result.
    """
    registry = _get_registry()

    # Step 1: Try AI-based DSL extraction if enabled
    dsl = DSLQuery()
    if request.use_ai and registry and registry.is_enabled:
        from osintote.ai.query_engine import IntentExtractor

        extractor = IntentExtractor(registry)
        dsl = await extractor.extract(request.query)

    # Step 2: Fallback to rule-based parsing
    if dsl.table == "records" and not dsl.filters:
        dsl = DSLParser.parse(request.query)

    # Step 3: Execute DSL query
    executor = DSLExecutor(get_async_session)
    result = executor.execute(dsl)

    # Step 4: Format as natural language
    text = NLFormatter.format(result)

    return {
        "query": request.query,
        "dsl": {
            "table": dsl.table,
            "columns": dsl.columns,
            "filters": dsl.filters,
            "order_by": dsl.order_by,
            "order_dir": dsl.order_dir,
            "limit": dsl.limit,
        },
        "count": result.count,
        "text": text,
        "records": result.records,
    }


@router.post("/analyze")
async def analyze_task(request: AnalyzeRequest) -> dict:
    """Run AI analysis on a task's findings.

    Parameters
    ----------
    request:
        AnalyzeRequest with task metadata and records.

    Returns
    -------
    dict:
        Analysis result with risk score, findings, and recommendations.
    """
    registry = _get_registry()
    if registry is None or not registry.is_enabled:
        raise HTTPException(
            status_code=503,
            detail="AI analysis is not enabled in configuration",
        )

    engine = AnalysisEngine(registry)
    result = await engine.analyze(
        target=request.target,
        records=request.records,
        task_type=request.task_type,
        task_id=request.task_id,
    )

    return result.to_dict()


@router.get("/models")
async def list_models() -> dict:
    """List available AI models.

    Returns
    -------
    dict:
        Available models and provider status.
    """
    registry = _get_registry()
    if registry is None:
        raise HTTPException(
            status_code=503,
            detail="AI is not configured",
        )

    available = await registry.is_available()
    models = []
    if available:
        models = await registry.list_models()

    return ModelListResponse(models=models, available=available).model_dump()


@router.get("/status")
async def ai_status() -> dict:
    """Get AI provider status.

    Returns
    -------
    dict:
        Provider availability and configuration status.
    """
    registry = _get_registry()
    if registry is None:
        return {
            "enabled": False,
            "available": False,
        }

    available = await registry.is_available()
    return {
        "enabled": registry.is_enabled,
        "available": available,
    }
