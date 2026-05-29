# CLI Reference

Complete reference for the `osintote` command-line interface.

## Commands

### `osintote init`

Initialize a new OSINTote project.

```bash
osintote init [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--force` | `False` | Overwrite existing config files |
| `-d, --db-path` | `osintote.db` | Path to the SQLite database file |
| `--on-complete` | `None` | Shell command to execute on task completion |

**Examples:**

```bash
# Initialize with default settings
osintote init

# Use a custom database path
osintote init --db-path /data/osintote.db

# Run a notification command on task completion
osintote init --on-complete "curl http://example.com/webhook"
```

### `osintote serve`

Start the OSINTote web API server.

```bash
osintote serve [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8000` | Bind port |

**Examples:**

```bash
# Start on default settings
osintote serve

# Bind to all interfaces
osintote serve --host 0.0.0.0 --port 8080
```

### `osintote status`

Display system status and configuration.

```bash
osintote status
```

Shows database path, configured callbacks, and available recipes.

### `osintote --help`

Show help and available commands.

## Callback Configuration

When using `--on-complete`, OSINTote creates a `.osintote/callbacks.json` file:

```json
{
  "callbacks": [
    {
      "command": "curl http://example.com/webhook",
      "enabled": true
    }
  ]
}
```

### Placeholder Substitution

Commands can use placeholders that are replaced at runtime:

| Placeholder | Replaced With |
|-------------|---------------|
| `{task_id}` | The UUID of the completed task |
| `{target}` | The target name |

**Example:**

```bash
osintote init --on-complete "echo '{task_id} {target} completed' >> /tmp/tasks.log"
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Configuration error |
| `3` | Database error |
