# ADR-001: Monolithic Package Architecture

**Status**: Accepted
**Date**: 2026-05-28

## Context

OSINTote is a multi-component application consisting of a Python backend (CLI, API, engine, models) and a SvelteKit frontend. We needed to decide on the package structure.

## Decision

Use a **monolithic `osintote/` package** in `src/osintote/` with a sibling `frontend/` directory.

```
OSINTote/
├── src/osintote/     # Python package (CLI, API, engine, models, crypto, logging)
├── frontend/         # SvelteKit Web UI
├── pyproject.toml    # Project configuration
└── Makefile          # Development shortcuts
```

### Rationale

- **Single entry point**: One `osintote` CLI command, one `pip install`
- **Shared dependencies**: Python and frontend share the same project root for configuration
- **Simple deployment**: Docker build can copy both components from the same repository
- **AI-navigable**: Single top-level package is easier for AI agents to understand than a monorepo

### Alternatives Considered

- **Monorepo with separate packages**: More complex tooling, separate versioning, more CI workflows
- **PyPI + npm packages**: Separated versioning, duplicate configuration, harder local development
- **Submodule structure**: Adds complexity without benefit for a small-to-medium project

## Consequences

- **Positive**: Simple setup, single lock file, easy to develop and test
- **Negative**: Python and frontend dependencies are managed separately (two lock files)
- **Mitigation**: `Makefile` provides unified commands for both ecosystems
