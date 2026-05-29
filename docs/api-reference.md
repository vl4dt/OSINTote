# API Reference

REST API specification for OSINTote. Base URL: `http://127.0.0.1:8000/api/`

Interactive API docs are available at: `http://127.0.0.1:8000/api/docs`

## Health

```
GET /api/health
```

Returns service status.

**Response**: `200 OK`
```json
{"status": "ok", "version": "0.1.0"}
```

## Targets

Target CRUD is managed through the Web UI. Targets are stored in SQLite and can be queried via the ORM.

**Columns**: `id`, `name`, `type` (domain/ip/url/email/custom), `status`, `tags`, `createdAt`, `updatedAt`

## Tasks

### Task CRUD

```
POST   /api/tasks              — Create a new task
GET    /api/tasks              — List tasks (query params: target_id, status, limit, offset)
GET    /api/tasks/{id}         — Get task details
PUT    /api/tasks/{id}         — Update task (partial)
DELETE /api/tasks/{id}         — Delete a task
```

**Status transitions**:

```
POST /api/tasks/{id}/start     — Transition PENDING → RUNNING
POST /api/tasks/{id}/cancel    — Transition RUNNING/PENDING → CANCELLED
POST /api/tasks/{id}/resume    — Transition PAUSED → RUNNING
```

**Response model** (`TaskRead`):
```json
{
  "id": "uuid",
  "name": "recon",
  "target_id": "uuid",
  "status": "pending",
  "recipe": "full-scan",
  "created_at": "2026-05-28T10:00:00Z",
  "updated_at": "2026-05-28T10:00:00Z",
  "started_at": null,
  "completed_at": null
}
```

### Task Events (SSE)

```
GET /api/tasks/{id}/events    — Snapshot of task events
GET /api/tasks/{id}/stream    — Real-time SSE progress stream
```

The **stream** endpoint returns Server-Sent Events in real-time:

- `task_started`: Task begins execution
- `progress`: Progress updates
- `stage_complete`: Individual stage completion with results
- `task_finished`: Final status (completed/failed/cancelled)

**SSE heartbeat**: 15s ping interval to keep connections alive.

## AI

### Natural Language Query

```
POST /api/ai/query
```

Converts natural language to a DSL query, executes it against the database, and returns formatted results.

**Request body**:
```json
{
  "query": "Show critical vulnerabilities",
  "use_ai": true
}
```

### Post-Task Analysis

```
POST /api/ai/analyze
```

Runs AI analysis on a completed task. Returns structured output with risk score, summary, and findings.

### Available Models

```
GET /api/ai/models            — List available AI models
GET /api/ai/status            — Check provider availability
```

## Logs (SSE)

```
GET /api/logs/stream          — Server-Sent Events log stream
GET /api/logs/export          — Export all logs as JSON
```

Returns structured JSON log records with fields: `timestamp`, `level`, `logger`, `message`, `task_id`, `stage`, `pid`.

## Errors

```
GET    /api/errors             — List all errors
GET    /api/errors/{id}        — Get error details
GET    /api/errors/stream      — SSE error stream
```

**Severity levels**: `info`, `warning`, `critical`, `blocking`

## API Keys

```
GET     /api/api-keys         — List all API keys
GET     /api/api-keys/{id}    — Get API key details
POST    /api/api-keys         — Create a new API key
PUT     /api/api-keys/{id}    — Update an API key
DELETE  /api/api-keys/{id}    — Delete an API key
PUT     /api/api-keys/{id}/rotate — Rotate the primary API key for a source
GET     /api/api-keys/resolve/{source} — Resolve the primary API key for a source
```

Keys are encrypted with AES-256-GCM. The `show` endpoint returns a masked key string.

## Webhooks

```
POST   /api/webhooks           — Create a webhook
GET    /api/webhooks           — List active webhooks
GET    /api/webhooks/{id}      — Get webhook
PUT    /api/webhooks/{id}      — Update webhook
DELETE /api/webhooks/{id}      — Delete webhook
POST   /api/webhooks/{id}/test — Test delivery
```

**Webhook payload**:
```json
{
  "event_type": "on_task_complete",
  "task_id": "uuid",
  "target_name": "example.com",
  "status": "completed",
  "timestamp": "2026-05-28T10:00:00Z"
}
```

**HMAC-SHA256 signature**: All webhook deliveries include the `X-Webhook-Signature` header for verification.

## Authentication

Currently, no authentication is required. Implement authentication before exposing to untrusted networks. See [Security](security.md).

## Error Responses

All errors follow the format:

```json
{
  "detail": "Error message"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request |
| 404 | Not found |
| 422 | Validation error |
| 500 | Internal server error |
| 503 | Service unavailable (executor not ready) |
