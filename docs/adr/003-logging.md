# ADR-003: Structured Logging Design

**Status**: Accepted
**Date**: 2026-05-28

## Context

OSINTote needs structured logging for both local development and production monitoring. Logs must be parseable, filterable, and streamable to the Web UI.

## Decision

Use **JSON-structured logging** with two output handlers:

1. **JSON file handler** — Rotating file logs with JSON format
2. **SSE log handler** — Streams structured log records to the Web UI via Server-Sent Events

### Components

- **JSONFormatter**: Custom logging formatter outputting JSON records
- **SSELogHandler**: Emits log records as SSE events
- **get_logger(name)**: Factory function that configures and returns a logger
- **setup_logging(path, level, sse_handler)**: One-shot configuration for the entire application

### Log Record Structure

```json
{
  "timestamp": "2026-05-28T12:00:00Z",
  "level": "INFO",
  "logger": "osintote.engine",
  "message": "stage completed",
  "task_id": "abc123",
  "pid": 12345
}
```

## Alternatives Considered

- **Python dictserializer**: Built-in, but no SSE support
- **structlog**: Powerful, but adds complexity and dependencies
- **loguru**: Simple, but less standard for production environments

## Consequences

- **Positive**: Logs are machine-parseable, filterable by any JSON field, streamable to UI
- **Negative**: Custom SSE handler needs careful connection management
- **Mitigation**: Use background tasks with proper cleanup to prevent resource leaks
