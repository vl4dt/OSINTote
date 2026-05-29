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

OSINTote consists of **two servers**:

| Server | Port | Description |
|--------|------|-------------|
| **Backend (FastAPI)** | `8000` | REST API, SSE streams, Swagger docs at `/api/docs` |
| **Frontend (Vite/SvelteKit)** | `5173` | Web UI (dark-themed 3-panel dashboard) |

Both must be running simultaneously for full functionality.

### Option 1: Dev Script (Recommended)

**Unix/macOS:**

```bash
# Start both servers
./scripts/dev.sh

# Or only one of them
./scripts/dev.sh api   # Backend only
./scripts/dev.sh ui    # Frontend only
```

**Windows (PowerShell):**

```powershell
# Start both servers
.\scripts\dev.ps1

# Or only one of them
.\scripts\dev.ps1 api   # Backend only
.\scripts\dev.ps1 ui    # Frontend only
```

### Option 2: Makefile (Unix/macOS only)

```bash
# Start both servers
make dev

# Or start them in separate terminals
osintote serve                        # Terminal 1 — backend
make dev                              # Terminal 2 — frontend (cd frontend && npm run dev)
```

> **Note:** `make dev` uses background jobs (`&`) which only work on Unix/macOS. On Windows, use the PowerShell dev script or open two terminals manually.

### Option 3: Manual (Two Terminals)

**Unix/macOS:**

```bash
# Terminal 1 — Backend API server
osintote serve

# Terminal 2 — Frontend dev server
cd frontend
npm run dev
```

**Windows (PowerShell):**

```powershell
# Terminal 1 — Backend API server
osintote serve

# Terminal 2 — Frontend dev server
cd frontend
npm run dev
```

### URLs After Starting

| URL | Description |
|-----|-------------|
| `http://localhost:5173` | Web UI (frontend dev server) |
| `http://127.0.0.1:8000` | Backend API server |
| `http://127.0.0.1:8000/api/docs` | Swagger UI (interactive API docs) |

### Production Build

```bash
# Build Docker image (multi-stage, multi-arch)
docker build -t osintote .

# Run with docker-compose
docker-compose up --build
```

### With Docker

```bash
docker-compose up --build
```

Builds a multi-stage Docker image and starts the service with SQLite persistence.

## Next Steps

- [CLI Reference](cli-reference.md) — Learn the command-line interface
- [Web UI Guide](web-ui-guide.md) — Explore the web dashboard
- [Security](security.md) — Understand the security model
