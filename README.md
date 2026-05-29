# OSINTote

> **Ultimate OSINT tool with AI-powered analysis, CLI + Web UI**

[![CI](https://github.com/vl4dt/OSINTote/actions/workflows/ci.yml/badge.svg)](https://github.com/vl4dt/OSINTote/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

OSINTote is a modular Open Source Intelligence (OSINT) collection and analysis platform with a **CLI**, a **Web UI**, and an extensible **engine pipeline**. It features:

- **Multi-stage pipeline**: DNS, HTTP probes, WHOIS, and custom recipes
- **AI-powered analysis**: Pluggable AI providers (OpenAI, Ollama, LMStudio, vLLM)
- **Web UI**: Dark-themed 3-panel dashboard with live SSE progress streaming
- **CLI**: Initialize projects, manage targets, run tasks, view results
- **Callback system**: Shell commands and webhook notifications on task completion
- **Encrypted storage**: AES-256-GCM for API keys and sensitive data
- **Structured logging**: JSON logs with SSE log streaming to the Web UI

## Quick Start

### Prerequisites

- Python 3.10+ with `uv` installed
- Node.js 20+ (for the Web UI frontend)

### Installation

```bash
# Clone and initialize
git clone https://github.com/vl4dt/OSINTote.git
cd OSINTote

# Create virtual environment and install dependencies
make init

# Activate the environment
source .venv/bin/activate   # Linux/macOS
# or .venv\Scripts\activate   # Windows
```

### First Run

```bash
# Initialize the project (creates config, database, migrations)
osintote init
```

**Start the dev servers (backend API + frontend UI):**

**Unix/macOS:**

```bash
./scripts/dev.sh
```

**Windows (PowerShell):**

```powershell
.\scripts\dev.ps1
```

**Or use make (Unix/macOS only):**

```bash
make dev
```

**Or start servers in separate terminals:**

```bash
osintote serve                    # Terminal 1 — backend API
make dev                          # Terminal 2 — frontend dev server
```

## Features

| Feature | Description |
|---------|-------------|
| **Targets** | Add and manage intelligence targets (domains, IPs, URLs) |
| **Tasks** | Run multi-stage reconnaissance pipelines against targets |
| **Results** | View collected records with severity ratings and source tracking |
| **Dashboard** | Real-time overview of active tasks, targets, and findings |
| **Recipes** | Pre-built and custom pipeline definitions (quick-scan, full-scan, passive-only) |
| **Webhooks** | Configure callbacks to receive notifications on task events |
| **AI Analysis** | Pluggable AI providers (OpenAI, Ollama, LMStudio, vLLM) with query engine, suggestions, and analysis |
| **Context Pruning** | Auto-summarize and prune context for token-efficient AI processing |
| **Relationship Graph** | vis.js-based interactive network graph of targets, hosts, and services |
| **Rate Limiter** | Per-source async semaphore with adaptive backoff on HTTP 429 |
| **Report Generation** | Export to JSON, Markdown, or standalone HTML (with vis.js network graphs) |

## CLI Reference

See [docs/cli-reference.md](./docs/cli-reference.md) for the complete CLI command reference.

### Commands

| Command | Description |
|---------|-------------|
| `osintote init` | Initialize a new OSINTote project |
| `osintote serve` | Start the web API server |
| `osintote status` | Check system status |
| `osintote api-key` | Manage API keys for external sources |
| `osintote recon` | Run reconnaissance pipelines |
| `osintote tasks` | Manage task lifecycle |
| `osintote recipes` | Manage reconnaissance recipes |
| `osintote settings` | Manage project settings |
| `osintote webhook` | Manage webhook subscriptions |

## Web UI Guide

See [docs/web-ui-guide.md](./docs/web-ui-guide.md) for a complete guide to using the Web UI.

### Pages

- **Dashboard** — Overview of active tasks, target counts, and recent findings
- **Targets** — Add, search, and manage intelligence targets
- **Tasks** — Run and monitor reconnaissance tasks with live SSE progress
- **Results** — View collected data, filter by severity, and examine details
- **Logs** — Real-time log streaming via Server-Sent Events with filtering and export
- **Settings** — AI configuration, default recipe, output format, and API key management

## API Reference

See [docs/api-reference.md](./docs/api-reference.md) for the full API specification.

## Security

See [docs/security.md](./docs/security.md) for security considerations, threat model, and hardening recommendations.

## Table of Contents

- [README](./README.md) — You are here
- [Getting Started](./docs/getting-started.md) — Installation and configuration
- [CLI Reference](./docs/cli-reference.md) — Complete command reference
- [Web UI Guide](./docs/web-ui-guide.md) — Web interface walkthrough
- [API Reference](./docs/api-reference.md) — REST API specification
- [Built-in Recipes](./docs/recipes/built-in.md) — Pre-built pipeline definitions
- [Custom Recipes](./docs/recipes/custom.md) — Writing your own recipes
- [Security](./docs/security.md) — Security model and best practices
- [FAQ](./docs/faq.md) — Frequently asked questions
- [ADR-001](./docs/adr/001-architecture.md) — Monolithic package architecture
- [ADR-002](./docs/adr/002-crypto.md) — Encryption strategy
- [ADR-003](./docs/adr/003-logging.md) — Structured logging design
- [ADR-004](./docs/adr/004-engine.md) — Pipeline engine design
- [ADR-005](./docs/adr/005-frontend.md) — Frontend architecture

## Architecture

```
OSINTote/
├── src/osintote/           # Python package
│   ├── ai/                 # AI providers, query engine, suggester, analysis
│   ├── api/                # FastAPI application + routers
│   ├── cli/                # CLI commands (Typer)
│   ├── engine/             # Pipeline engine & recipe system
│   ├── models/             # SQLAlchemy/SQLModel ORM models
│   ├── notify/             # Callback system (webhooks, shell commands)
│   ├── recipes/            # Recipe definitions and loader
│   ├── reports/            # Report generation (JSON, Markdown, HTML)
│   ├── workers/            # Data source stages (DNS, HTTP, nmap, nuclei, etc.)
│   ├── crypto.py           # AES-256-GCM encryption utilities
│   ├── logging_config.py   # Structured JSON/SSE logging
│   └── __about__.py        # Package metadata
├── frontend/               # SvelteKit Web UI (Svelte 5, Tailwind CSS 4)
│   ├── src/lib/            # Shared components + API client
│   ├── src/routes/         # Page routes
│   └── static/             # Static assets
├── docs/                   # Documentation + ADRs
│   └── adr/                # Architecture Decision Records
├── .beads/                 # Beads issue tracking database
├── pyproject.toml          # Project configuration (hatch + uv)
├── Makefile                # Development shortcuts
├── Dockerfile              # Multi-stage Docker build
├── docker-compose.yml      # Local development compose
└── uv.lock                 # Dependency lock file
```

## Packaging & Deployment

OSINTote is packaged for PyPI using hatch:

```bash
# Build sdist + wheel
make build

# Upload to PyPI (requires twine)
twine upload dist/*
```

Docker multi-stage build publishes to ghcr.io:

```bash
# Build for local use
docker build -t osintote .

# Multi-arch build (CI automated)
docker buildx build --platform linux/amd64,linux/arm64 -t ghcr.io/vl4dt/osintote:latest --push .
```

## Development

```bash
# Run tests
make test

# Run tests with coverage
make test-cov

# Format code
make fmt

# Lint + type check (ruff + mypy)
make check

# Build the package
make build
```

### Pre-commit Hooks

The project uses pre-commit hooks for quality enforcement:

- **ruff** — Linting and formatting
- **mypy** — Static type checking
- **Trim trailing whitespace** — Whitespace cleanup
- **End of file** — Ensure trailing newline

## License

This project is licensed under the [MIT License](LICENSE).

## Project Status

| Epic | Tasks | Completion |
|------|-------|------------|
| Foundation (enz) | 8 | 100% |
| Pipeline & Engine (yk2) | 12 | 100% |
| Data Sources (jcz) | 12 | 100% |
| Polish & Ship (35e) | 12 | 100% |
| Intelligence & AI (2yq) | 8 | 100% |
| **Total** | **52** | **100%** |
