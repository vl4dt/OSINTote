# API Reference

REST API specification for OSINTote. Base URL: `http://127.0.0.1:8000/api/v1/`

## Endpoints

### Health

```
GET /api/v1/health
```

Returns service status.

**Response**: `200 OK`
```json
{"status": "ok"}
```

### Targets

```
GET    /api/v1/targets         # List all targets
POST   /api/v1/targets         # Create a target
GET    /api/v1/targets/{id}    # Get target details
PUT    /api/v1/targets/{id}    # Update a target
DELETE /api/v1/targets/{id}    # Delete a target
```

### Tasks

```
GET    /api/v1/tasks           # List all tasks
POST   /api/v1/tasks           # Create a task
GET    /api/v1/tasks/{id}      # Get task details
PUT    /api/v1/tasks/{id}      # Update a task
DELETE /api/v1/tasks/{id}      # Delete a task
```

### Results

```
GET    /api/v1/results         # List all results
GET    /api/v1/results/{id}    # Get result details
```

### Logs (SSE)

```
GET    /api/v1/logs/sse        # Server-Sent Events log stream
```

Returns a stream of JSON log records. Clients should handle reconnects.

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
