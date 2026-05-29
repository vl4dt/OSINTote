# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""AI query engine — natural-language → DSL → SQL pipeline.

Provides:
    - DSL parser and generator
    - AI intent extraction from natural language queries
    - SQL translation from DSL
    - Result formatting with natural language summary

Usage::

    from osintote.ai.query_engine import QueryEngine

    engine = QueryEngine()
    result = await engine.execute("Show all critical vulnerabilities")
    print(result.text)
    for rec in result.records:
        print(rec)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from sqlmodel import Session, select

from ..models.orm import Record, Task
from .provider import AIProviderRegistry

logger = logging.getLogger(__name__)


# ── DSL ─────────────────────────────────────────────────────────────────


@dataclass
class DSLQuery:
    """Domain-specific language query.

    Attributes
    ----------
    table:
        Target table (records, tasks, targets).
    columns:
        Columns to select.
    filters:
        List of filter conditions.
    order_by:
        Sort field.
    order_dir:
        Sort direction (asc/desc).
    limit:
        Maximum results.
    """

    table: str = "records"
    columns: list[str] = field(default_factory=lambda: ["*"])
    filters: list[dict[str, Any]] = field(default_factory=list)
    order_by: str | None = None
    order_dir: str = "desc"
    limit: int = 100


# ── Result ──────────────────────────────────────────────────────────────


@dataclass
class QueryResult:
    """Result of a query execution.

    Attributes
    ----------
    records:
        Matching records.
    text:
        Natural language summary.
    count:
        Total number of matching records.
    dsl:
        DSL that was executed.
    """

    records: list[dict[str, Any]] = field(default_factory=list)
    text: str = ""
    count: int = 0
    dsl: DSLQuery | None = None


# ── Parser ──────────────────────────────────────────────────────────────


class DSLParser:
    """Parse DSL query strings into DSLQuery objects.

    DSL syntax::

        SELECT <columns> FROM <table> [WHERE <condition>] [ORDER BY <col> [ASC|DESC]] [LIMIT <n>]

    Examples::

        SELECT * FROM records WHERE severity='critical'
        SELECT count(*) FROM tasks WHERE status='running'
        SELECT name FROM targets
    """

    TABLES = {"records", "tasks", "targets"}

    @classmethod
    def parse(cls, dsl: str) -> DSLQuery:
        """Parse a DSL query string.

        Parameters
        ----------
        dsl:
            DSL query string.

        Returns
        -------
        DSLQuery
            Parsed query object.
        """
        dsl = dsl.strip().rstrip(";")
        query = DSLQuery()

        # Parse SELECT ... FROM
        select_match = re.match(
            r"SELECT\s+(.+?)\s+FROM\s+(\w+)", dsl, re.IGNORECASE
        )
        if not select_match:
            query.table = "records"
            return query

        columns_str = select_match.group(1).strip()
        query.table = select_match.group(2).lower()
        query.columns = [c.strip() for c in columns_str.split(",")]

        if query.table not in cls.TABLES:
            query.table = "records"

        rest = dsl[select_match.end():].strip()

        # Parse WHERE (stop before ORDER BY or LIMIT)
        where_match = re.match(
            r"WHERE\s+(.+?)(?=\s+ORDER\s+BY\b|\s+LIMIT\b|$)", rest, re.IGNORECASE
        )
        if where_match:
            where_clause = where_match.group(1).strip()
            query.filters = cls._parse_where(where_clause)
            rest = rest[where_match.end():].strip()

        # Parse ORDER BY
        order_match = re.match(
            r"ORDER\s+BY\s+(\w+)\s*(ASC|DESC)?", rest, re.IGNORECASE
        )
        if order_match:
            query.order_by = order_match.group(1).lower()
            query.order_dir = (order_match.group(2) or "DESC").upper()
            rest = rest[order_match.end():].strip()

        # Parse LIMIT
        limit_match = re.match(r"LIMIT\s+(\d+)", rest, re.IGNORECASE)
        if limit_match:
            query.limit = int(limit_match.group(1))
            rest = rest[limit_match.end():].strip()

        return query

    @classmethod
    def _parse_where(cls, where: str) -> list[dict[str, Any]]:
        """Parse a WHERE clause into filter conditions."""
        filters: list[dict[str, Any]] = []

        # Split on AND/OR
        parts = re.split(r"\s+(AND|OR)\s+", where, flags=re.IGNORECASE)
        current_filter: dict[str, Any] = {}

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check for logical operator
            if part.upper() in ("AND", "OR"):
                if current_filter:
                    current_filter["logic"] = part.upper()
                    filters.append(current_filter)
                current_filter = {}
                continue

            # Parse condition: column operator value
            cond = re.match(r"(\w+)\s*(=|!=|<>|>=|<=|>|<|LIKE|NOT\s+LIKE)\s*(.+)", part, re.IGNORECASE)
            if cond:
                current_filter = {
                    "column": cond.group(1).lower(),
                    "operator": cond.group(2).upper(),
                    "value": cond.group(3).strip().strip("'\"`"),
                }
            elif current_filter and not current_filter.get("value"):
                # Implicit equality
                current_filter["operator"] = "="
                current_filter["value"] = part.strip().strip("'\"`")

        if current_filter:
            filters.append(current_filter)

        return filters


# ── Executor ────────────────────────────────────────────────────────────


class DSLExecutor:
    """Execute a DSLQuery against the database.

    Parameters
    ----------
    session_factory:
        Function returning a SQLModel Session.
    """

    def __init__(self, session_factory) -> None:  # type: ignore[type-arg]
        """Initialize with a session factory function."""
        self._factory = session_factory

    def execute(self, dsl: DSLQuery) -> QueryResult:
        """Execute a DSL query against the database.

        Parameters
        ----------
        dsl:
            DSL query to execute.

        Returns
        -------
        QueryResult
            Query results with records and count.
        """
        with self._factory() as session:
            # Map table to model
            model_map = {
                "records": Record,
                "tasks": Task,
                "targets": Record,  # Use Record as fallback
            }
            model = model_map.get(dsl.table, Record)

            stmt = select(model)

            # Apply filters
            for f in dsl.filters:
                column = f.get("column", "")
                operator = f.get("operator", "=")
                value = f.get("value", "")

                # Map column to model field
                field_map = {
                    "severity": "severity",
                    "type": "type",
                    "target": "target",
                    "status": "status",
                    "message": "message",
                    "level": "level",
                    "logger": "logger",
                    "name": "name",
                }
                field_name = field_map.get(column, column)

                if hasattr(model, field_name):
                    if operator in ("=", "LIKE"):
                        stmt = stmt.where(getattr(model, field_name) == value)
                    elif operator == "!=":
                        stmt = stmt.where(getattr(model, field_name) != value)
                    elif operator == "NOT LIKE":
                        stmt = stmt.where(getattr(model, field_name) != value)
                    elif operator == ">=":
                        stmt = stmt.where(getattr(model, field_name) >= value)
                    elif operator == "<=":
                        stmt = stmt.where(getattr(model, field_name) <= value)
                    elif operator == ">":
                        stmt = stmt.where(getattr(model, field_name) > value)
                    elif operator == "<":
                        stmt = stmt.where(getattr(model, field_name) < value)

            # Apply ordering
            if dsl.order_by:
                order_field = dsl.order_by
                if hasattr(model, order_field):
                    if dsl.order_dir == "DESC":
                        stmt = stmt.order_by(getattr(model, order_field).desc())
                    else:
                        stmt = stmt.order_by(getattr(model, order_field).asc())

            # Apply limit
            stmt = stmt.limit(dsl.limit)

            # Execute
            results = session.exec(stmt).all()

            # Convert to dicts
            records = []
            for r in results:
                try:
                    records.append(r.model_dump())
                except Exception:
                    records.append({})

            return QueryResult(
                records=records,
                count=len(results),
                dsl=dsl,
            )


# ── Intent Extractor (AI-powered) ──────────────────────────────────────


class IntentExtractor:
    """Extract query intent from natural language using AI.

    Parameters
    ----------
    registry:
        AI provider registry.
    """

    def __init__(self, registry: AIProviderRegistry) -> None:
        """Initialize with an AI provider registry."""
        self.registry = registry

    async def extract(self, nl_query: str) -> DSLQuery:
        """Convert natural language to DSL.

        Parameters
        ----------
        nl_query:
            Natural language query.

        Returns
        -------
        DSLQuery
            Parsed DSL query.
        """
        system_prompt = (
            "You are a database query translator. Convert natural language "
            "into a simplified SQL-like DSL query. Available tables: "
            "records (columns: id, type, severity, message, target, data, timestamp), "
            "tasks (columns: id, name, status, type, target_id, recordsCount, createdAt), "
            "targets (columns: id, name, type, status, tags, createdAt).\n\n"
            "Return ONLY the DSL query as a plain string, no explanation.\n"
            "DSL syntax: SELECT <cols> FROM <table> WHERE <condition> ORDER BY <col> [ASC|DESC] LIMIT <n>\n\n"
            "Examples:\n"
            "  'Show critical vulnerabilities' → SELECT * FROM records WHERE severity='critical' ORDER BY severity DESC\n"
            "  'Count running tasks' → SELECT count(*) FROM tasks WHERE status='running'\n"
            "  'List targets with admin' → SELECT name FROM targets WHERE tags LIKE 'admin'\n"
        )

        raw = await self.registry.query(
            f"Convert to DSL: {nl_query}",
            system_prompt=system_prompt,
        )
        return DSLParser.parse(raw) if raw else DSLQuery()


# ── NL Formatter ────────────────────────────────────────────────────────


class NLFormatter:
    """Format query results as natural language."""

    @staticmethod
    def format(result: QueryResult) -> str:
        """Format query results as natural language.

        Parameters
        ----------
        result:
            QueryResult to format.

        Returns
        -------
        str
            Human-readable summary.
        """
        if result.count == 0:
            return "No records matched your query."

        summary = f"Found {result.count} record(s):\n\n"
        for i, rec in enumerate(result.records[:20], 1):
            sev = rec.get("severity", "")
            rec_type = rec.get("type", "")
            msg = rec.get("message", "")
            target = rec.get("target", "")
            summary += f"  {i}. [{sev}] {rec_type}: {msg}"
            if target:
                summary += f" (target: {target})"
            summary += "\n"

        if result.count > 20:
            summary += f"\n  ... and {result.count - 20} more records"

        return summary

    @staticmethod
    def format_count(result: QueryResult) -> str:
        """Format a count-only result.

        Parameters
        ----------
        result:
            QueryResult with count.

        Returns
        -------
        str
            Count summary.
        """
        if result.count == 0:
            return "No matching records found."

        return f"Total: {result.count} record(s)"


# ── QueryEngine (convenience wrapper) ──────────────────────────────────


class QueryEngine:
    """Convenience wrapper around DSL pipeline.

    Provides a simple interface: parse → execute → format.

    Parameters
    ----------
    session_factory:
        Function returning a Session.
    """

    def __init__(self, session_factory=None) -> None:  # type: ignore[type-arg]
        """Initialize with an optional session factory."""
        self.executor = DSLExecutor(session_factory) if session_factory else None
        self.parser = DSLParser()
        self.formatter = NLFormatter()

    def execute(self, query: str) -> QueryResult:
        """Execute a DSL or NL query.

        Parameters
        ----------
        query:
            DSL query string or natural language query.

        Returns
        -------
        QueryResult
            Query results.
        """
        dsl = DSLParser.parse(query)
        if self.executor:
            return self.executor.execute(dsl)
        return QueryResult(count=0, dsl=dsl)

    async def execute_nl(
        self,
        nl_query: str,
        registry: AIProviderRegistry,
    ) -> QueryResult:
        """Execute a natural language query via AI intent extraction.

        Parameters
        ----------
        nl_query:
            Natural language query.
        registry:
            AI provider registry.

        Returns
        -------
        QueryResult
            Query results.
        """
        extractor = IntentExtractor(registry)
        dsl = await extractor.extract(nl_query)
        if self.executor:
            return self.executor.execute(dsl)
        return QueryResult(count=0, dsl=dsl)
