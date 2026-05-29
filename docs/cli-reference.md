# CLI Reference

Complete reference for the `osintote` command-line interface.

## Top-Level Commands

| Command | Description |
|---------|-------------|
| `osintote init` | Initialize a new OSINTote project |
| `osintote serve` | Start the web API server |
| `osintote status` | Show OSINTote system status |
| `osintote api-key` | Manage API keys |
| `osintote recon` | Recon execution commands |
| `osintote recipes` | Recipe management commands |
| `osintote settings` | Settings management commands |
| `osintote tasks` | Task management commands |
| `osintote webhook` | Manage webhook subscriptions |

## `osintote init`

Initialize a new OSINTote project. Creates the `.osintote/` config directory, default `config.json`, and the SQLite database.

```bash
osintote init [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--force` | `False` | Overwrite existing config files |
| `-d, --db-path` | `osintote.db` | Path to the SQLite database file |

**Examples:**

```bash
# Initialize with default settings
osintote init

# Use a custom database path
osintote init --db-path /data/osintote.db

# Force re-initialization
osintote init --force
```

## `osintote serve`

Start the OSINTote web API server. Runs migrations on startup and serves the FastAPI app with Uvicorn.

```bash
osintote serve [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--host, -h` | `127.0.0.1` | Bind address |
| `--port, -p` | `8000` | Bind port |
| `--reload, -r` | `False` | Enable auto-reload for development |
| `--notify` | `False` | Enable desktop notifications |

**Examples:**

```bash
# Start on default settings
osintote serve

# Bind to all interfaces with notifications
osintote serve --host 0.0.0.0 --port 8080 --notify

# Development mode with hot-reload
osintote serve --reload
```

Interactive API documentation is available at `http://127.0.0.1:8000/api/docs` (Swagger UI).

## `osintote status`

Display OSINTote system status including version, database path, and entity counts.

```bash
osintote status
```

Shows:
- Version
- Project path
- Database existence and path
- Entity counts (targets, records, tasks, API keys, webhooks, settings)

## `osintote api-key`

Manage API keys for external OSINT sources. Keys are encrypted with AES-256-GCM before storage.

### `osintote api-key add`

Add a new API key for an external OSINT source.

```bash
osintote api-key add NAME SOURCE KEY [OPTIONS]
```

**Arguments:**
- `NAME` — Key name (required)
- `SOURCE` — Source name (`shodan`, `virustotal`, `openai`, `ollama`, `lmstudio`, `vllm`) (required)
- `KEY` — API key/credential value (required)

**Options:**
| Option | Description |
|--------|-------------|
| `-p, --primary` | Set as primary key for this source |
| `-f, --fallback` | Set as fallback key |
| `-t, --target` | Associate with a target ID |

**Examples:**

```bash
# Add a Shodan API key and set as primary
osintote api-key add shodan-primary shodan SHODAN_KEY_HERE --primary

# Add a VirusTotal key associated with a target
osintote api-key add vt-key virustotal VT_KEY_HERE --target abc-123
```

### `osintote api-key list`

List all API keys.

```bash
osintote api-key list
```

Shows key name, source, primary/fallback status, and masked key value.

### `osintote api-key show`

Show full details of a specific API key.

```bash
osintote api-key show KEY_ID
```

### `osintote api-key rotate`

Rotate the primary API key for a source. Deactivates the current primary and sets the new key as primary.

```bash
osintote api-key rotate SOURCE NEW_KEY [OPTIONS]
```

**Arguments:**
- `SOURCE` — Source name (required)
- `NEW_KEY` — New API key value (required)

**Options:**
| Option | Description |
|--------|-------------|
| `-n, --name` | New key name |

## `osintote recon`

Recon execution commands for running multi-stage intelligence pipelines.

### `osintote recon start`

Run a recon task against a target with rich progress display.

```bash
osintote recon start TARGET_NAME [OPTIONS]
```

**Arguments:**
- `TARGET_NAME` — Target to run recon against (required)

**Options:**
| Option | Description |
|--------|-------------|
| `-r, --recipe` | Recipe identifier (e.g., `quick-scan`, `full-scan`, `passive-only`) |
| `-n, --name` | Task name (default: `recon`) |
| `--dry-run` | Validate recipe without executing |
| `--no-live` | Disable live progress display |

**Examples:**

```bash
# Run quick scan against a domain
osintote recon start example.com

# Full scan with custom task name
osintote recon start example.com --recipe full-scan --name "deep-dive"

# Passive reconnaissance only
osintote recon start example.com --recipe passive-only --no-live

# Dry run to validate recipe
osintote recon start example.com --dry-run
```

### `osintote recon list`

List recon tasks with status indicators.

```bash
osintote recon list [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-t, --target` | Filter by target name |
| `-s, --status` | Filter by status |

## `osintote tasks`

Task management commands for the task lifecycle API.

### `osintote tasks create`

Create a new task and add it to the queue.

```bash
osintote tasks create TARGET_NAME [OPTIONS]
```

**Arguments:**
- `TARGET_NAME` — Target name (required)

**Options:**
| Option | Description |
|--------|-------------|
| `-n, --name` | Task name (required) |
| `-d, --description` | Task description |
| `-r, --recipe` | Recipe identifier |

### `osintote tasks list`

List tasks with optional filters.

```bash
osintote tasks list [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--target` | Filter by target ID |
| `--status` | Filter by status (pending, running, completed, failed, cancelled) |

### `osintote tasks show`

Show details of a specific task.

```bash
osintote tasks show TASK_ID
```

### `osintote tasks start`

Start a pending task (transitions to RUNNING).

```bash
osintote tasks start TASK_ID
```

### `osintote tasks cancel`

Cancel a running or pending task.

```bash
osintote tasks cancel TASK_ID
```

### `osintote tasks delete`

Delete a task and its associated errors/logs.

```bash
osintote tasks delete TASK_ID
```

## `osintote settings`

Settings management commands. Settings are stored in SQLite.

### `osintote settings get`

Get a setting value.

```bash
osintote settings get KEY
```

### `osintote settings set`

Set a setting value.

```bash
osintote settings set KEY VALUE [OPTIONS]
```

**Arguments:**
- `KEY` — Setting key (required)
- `VALUE` — Setting value (required)

**Options:**
| Option | Description |
|--------|-------------|
| `--description` | Setting description |

### `osintote settings list`

List all settings.

```bash
osintote settings list
```

### `osintote settings notifications`

Toggle desktop notifications.

```bash
osintote settings notifications
```

## `osintote webhook`

Manage webhook subscriptions for event-based notifications.

### `osintote webhook add`

Add a new webhook subscription.

```bash
osintote webhook add NAME URL [OPTIONS]
```

**Arguments:**
- `NAME` — Webhook name (required)
- `URL` — Webhook endpoint URL (required)

**Options:**
| Option | Description |
|--------|-------------|
| `-e, --events` | Comma-separated event types: `on_task_complete`, `on_task_fail`, `on_critical_finding` (default: `on_task_complete`) |
| `-s, --secret` | HMAC-SHA256 signing secret |
| `--disabled` | Disable the webhook |

**Examples:**

```bash
# Basic webhook on task completion
osintote webhook add my-hook https://example.com/webhook

# With HMAC signing and multiple events
osintote webhook add secure-hook https://example.com/webhook \
  --events on_task_complete,on_task_fail,on_critical_finding \
  --secret my-secret-key
```

### `osintote webhook list`

List active webhooks.

```bash
osintote webhook list
```

### `osintote webhook delete`

Delete a webhook.

```bash
osintote webhook delete WEBHOOK_ID
```

### `osintote webhook test`

Test webhook delivery.

```bash
osintote webhook test WEBHOOK_ID
```

Sends a test event to the webhook URL and returns the delivery result.

## `osintote recipes`

Recipe management commands for custom reconnaissance pipelines.

### `osintote recipes list`

List all available recipes (bundled defaults + user overrides).

```bash
osintote recipes list
```

### `osintote recipes show`

Show details of a specific recipe.

```bash
osintote recipes show RECIPE_NAME
```

### `osintote recipes save`

Save a new recipe (creates user override in `.osintote/recipes/`).

```bash
osintote recipes save NAME [OPTIONS]
```

**Arguments:**
- `NAME` — Recipe name (required)

**Options:**
| Option | Description |
|--------|-------------|
| `-d, --description` | Recipe description |
| `-s, --stages` | Comma-separated stage names (e.g., `dns-enumerate,http-probe,nmap`) |
| `-dp, --depends` | Dependency map (`stage:dep1,dep2`, e.g., `http-probe:dns-enumerate`) |

**Example:**

```bash
# Custom recipe with dependencies
osintote recipes save custom-full \
  --description "Custom deep scan" \
  --stages "dns-enumerate,http-probe,nmap,nuclei,whois" \
  --depends "http-probe:dns-enumerate,nmap:http-probe"
```

### `osintote recipes delete`

Delete a user-defined recipe (overrides only; bundled recipes cannot be deleted).

```bash
osintote recipes delete RECIPE_NAME
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Configuration error |
| `3` | Database error |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OSINTOTE_DB_PATH` | Override database path | `osintote.db` |
| `OSINTOTE_CONFIG_DIR` | Override config directory | `.osintote` |
