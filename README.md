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

# Start the web server
osintote serve

# Or start the development server with hot-reload
make dev
```

## Features

| Feature | Description |
|---------|-------------|
| **Targets** | Add and manage intelligence targets (domains, IPs, URLs) |
| **Tasks** | Run multi-stage reconnaissance pipelines against targets |
| **Results** | View collected records with severity ratings and source tracking |
| **Dashboard** | Real-time overview of active tasks, targets, and findings |
| **Recipes** | Pre-built and custom pipeline definitions for common OSINT workflows |
| **Webhooks** | Configure callbacks to receive notifications on task events |
| **AI Analysis** | Intelligent target classification, anomaly detection, and report generation |

## CLI Reference

See [docs/cli-reference.md](./docs/cli-reference.md) for the complete CLI command reference.

### Commands

| Command | Description |
|---------|-------------|
| `osintote init` | Initialize a new OSINTote project |
| `osintote serve` | Start the web API server |
| `osintote status` | Check system status |
| `osintote --help` | Show help and available commands |

## Web UI Guide

See [docs/web-ui-guide.md](./docs/web-ui-guide.md) for a complete guide to using the Web UI.

### Pages

- **Dashboard** — Overview of active tasks, target counts, and recent findings
- **Targets** — Add, search, and manage intelligence targets
- **Tasks** — Run and monitor reconnaissance tasks with live progress
- **Results** — View collected data, filter by severity, and examine details

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
│   ├── api/                # FastAPI application + routers
│   ├── cli/                # CLI commands (Typer)
│   ├── engine/             # Pipeline engine & recipe system
│   ├── models/             # SQLAlchemy/SQLModel ORM models
│   ├── notify/             # Callback system (webhooks, shell commands)
│   ├── reports/            # Report generation
│   ├── sources/            # Data source implementations
│   ├── crypto.py           # AES-256-GCM encryption utilities
│   ├── logging_config.py   # Structured JSON/SSE logging
│   └── __about__.py        # Package metadata
├── frontend/               # SvelteKit Web UI
│   ├── src/lib/            # Shared components + API client
│   ├── src/routes/         # Page routes
│   └── static/             # Static assets
├── docs/                   # Documentation
├── .beads/                 # Beads issue tracking database
├── pyproject.toml          # Project configuration (hatch + uv)
├── Makefile                # Development shortcuts
└── uv.lock                 # Dependency lock file
```

## Development

```bash
# Run tests
make test

# Run tests with coverage
make test-cov

# Format code
make fmt

# Lint + type check
make check

# Build the package
make build
```

## License

This project is licensed under the [MIT License](LICENSE).
