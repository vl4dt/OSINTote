# Getting Started

This guide walks you through installing, configuring, and running OSINTote.

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/vl4dt/OSINTote.git
cd OSINTote

# Initialize the project
make init
```

The `make init` command creates a virtual environment, installs all dependencies, and generates the `uv.lock` lock file.

### Manual Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS

# Install in editable mode
uv pip install -e .

# Install frontend dependencies
cd frontend && npm install && cd ..
```

## Configuration

### Project Initialization

After cloning, initialize the project with:

```bash
osintote init
```

This creates:
- `.osintote/config.json` — Project configuration (database path, listen address, port)
- `.osintote/callbacks.json` — Callback configuration (if `--on-complete` is specified)
- `osintote.db` — SQLite database
- Alembic migration directory — Automatic schema migrations

### Configuration File

```json
{
  "version": "0.0.1",
  "database": "osintote.db",
  "listen_host": "127.0.0.1",
  "listen_port": 8000
}
```

| Key | Default | Description |
|-----|---------|-------------|
| `version` | `0.0.1` | OSINTote version |
| `database` | `osintote.db` | Path to the SQLite database |
| `listen_host` | `127.0.0.1` | API server bind address |
| `listen_port` | `8000` | API server port |

## Running OSINTote

### Web Server

```bash
osintote serve
```

The server starts at `http://127.0.0.1:8000` by default. The API is available at `/api/v1/`.

### Development Mode

```bash
make dev
```

Runs both the API server and the SvelteKit frontend with hot-reload enabled.

### With Docker

```bash
docker-compose up --build
```

Builds a multi-stage Docker image and starts the service with SQLite persistence.

## Next Steps

- [CLI Reference](cli-reference.md) — Learn the command-line interface
- [Web UI Guide](web-ui-guide.md) — Explore the web dashboard
- [Security](security.md) — Understand the security model
