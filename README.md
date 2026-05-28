# OSINTote

**Ultimate OSINT tool** with AI-powered analysis, CLI + Web UI.

> A comprehensive open-source OSINT framework with SQLite-backed task management, automated recon, and intelligent analysis.

## 🚀 Quick Start

```bash
# Install
pip install osintote

# Initialize
osintote init

# Start web server
osintote serve

# Or CLI mode
osintote status
```

## ✨ Features

- **CLI + Web UI** — Full-featured terminal interface and responsive web dashboard
- **AI-Powered Analysis** — Provider-agnostic AI (Ollama, LM Studio, OpenAI, vLLM) for intelligent findings
- **Automated Recon** — DNS enumeration, HTTP probing, port scanning, WHOIS, Shodan, VirusTotal, Nuclei
- **SQLite Backend** — Write-ahead logging with auto-migrations and crash recovery
- **Recipe System** — JSON-based recon workflows with dependency-ordered stages
- **Real-time Progress** — SSE streaming for live task updates
- **Multi-Source Integration** — Pluggable engine architecture for 10+ OSINT sources

## 📦 Installation

```bash
# From PyPI
pip install osintote

# From source
git clone https://github.com/RicardoA-Salgado/osintote.git
cd osintote
pip install -e .
```

### Prerequisites

- Python 3.14+
- Node.js 20+ (for web UI development)

## 📖 Documentation

- [Getting Started](docs/getting-started.md)
- [CLI Reference](docs/cli-reference.md)
- [Web UI Guide](docs/web-ui-guide.md)
- [API Reference](docs/api-reference.md)
- [Built-in Recipes](docs/recipes/built-in.md)
- [Custom Recipes](docs/recipes/custom.md)
- [Security](docs/security.md)
- [FAQ](docs/faq.md)

## 🏗 Architecture

```
osintote/
├── cli/           # CLI commands (typer)
├── api/           # FastAPI web server
├── engine/        # OSINT engine + stage strategies
├── models/        # ORM models + database layer
├── workers/       # Background task executor
├── recipes/       # Built-in recon recipes
├── reports/       # Report generation service
└── tests/         # Test suite
```

## 🔧 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint and format
ruff check
ruff format

# Type checking
mypy src/osintote
```

## 📄 License

MIT License — see [LICENSE](LICENSE.txt) for details.

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## 🔗 Links

- [GitHub](https://github.com/RicardoA-Salgado/osintote)
- [Issues](https://github.com/RicardoA-Salgado/osintote/issues)
- [Documentation](https://github.com/RicardoA-Salgado/osintote#readme)
