# ADR-004: Pipeline Engine Design

**Status**: Accepted
**Date**: 2026-05-28

## Context

OSINTote needs an extensible pipeline engine that can run multiple reconnaissance stages (DNS, HTTP, WHOIS) against targets in a configurable order.

## Decision

Use a **stage-based strategy pattern** with a **recipe registry**.

### Components

- **Stage**: Abstract base class with an `execute(context)` method
- **StageContext**: Dataclass carrying task state between stages
- **StageResult**: Dataclass with stage output and metadata
- **STAGE_REGISTRY**: Dict mapping stage names to implementations
- **Recipe**: Defines the ordered list of stages to run

### Stage Lifecycle

```
Recipe → Stage Registry → Stage.execute() → StageResult → Next Stage
```

Each stage receives the full context, can modify it, and returns results that are persisted to the database.

## Alternatives Considered

- **DAG-based engine**: More flexible but complex to implement and debug
- **Workflow engine (Airflow, Prefect)**: Overkill for a single-user OSINT tool
- **Simple for-loop**: Too rigid, doesn't support dynamic stage selection

## Consequences

- **Positive**: Easy to add new stages, testable in isolation, recipes define clear execution order
- **Negative**: Context data sharing between stages couples them
- **Mitigation**: StageResult defines a clear interface; stages should only depend on documented context fields
