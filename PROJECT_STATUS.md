# OSINTOTE � Project Status Map

> Last updated: 2026-05-29

## Summary

```
OVERALL  [COMPLETE]         [ +++++++++++++++++++++++++++++++++++++++++++++++++++++++ ]  57/57 (100%) | 0 remaining | 0 blocked
```

| Epic | Status | Done/Total | % |
|------|--------|-----------|---|
| **Frontend & Reporting (2yq)** | COMPLETE | 9/9 | 100% |
| **Polish & Ship (35e)** | COMPLETE | 13/13 | 100% |
| **Foundation (enz)** | COMPLETE | 9/9 | 100% |
| **Data Sources & Intelligence (jcz)** | COMPLETE | 13/13 | 100% |
| **Pipeline & Engine (yk2)** | COMPLETE | 13/13 | 100% | |

---

## Frontend & Reporting (2yq) � COMPLETE

| Status | ID | Description |
|--------|----|-------------|
| x | OSINTote-2yq | Epic: Intelligence & AI — AI integration, context pruning, report generation, graph, natural language query |
| x | OSINTote-2yq.7 | Context pruning system — auto-summarizer (rule-based stats: domain count, IP count, port count, vuln count), smart context builder (executive summary, top findings, infrastructure, threat intel), token limits (~5K context) |
| x | OSINTote-2yq.3 | Report generation service — Reporter service, JSON export (always available), Markdown export (human-readable with tables/summary/risk score), HTML export (standalone with embedded data + vis.js + vanilla JS interactivity + print CSS) |
| o | OSINTote-2yq.4 | Relationship graph — vis.js Network with custom theming (node colors/shapes by type, edge labels by relationship type), zoom/pan, click-to-expand, layout toggle (force-directed/hierarchical), filter by type, max 500 nodes |
| x | OSINTote-2yq.2 | Webhook system — Webhook model, configurable endpoints (/api/webhooks), event triggers (on_task_complete, on_critical_finding), webhook payload structure, CLI add/remove/list, JSON config storage |
| x | OSINTote-2yq.1 | AI provider abstraction — AIProvider interface (analyze/query/suggest methods), OpenAICompatibleHTTP base class, provider-specific extensions (Ollama, LMStudio, llama.cpp, vLLM), AIProviderRegistry, AI models, provider auto-discovery via /v1/models |
| x | OSINTote-2yq.5 | AI workflow suggestions — post-task recommendations list, critical finding detection (rule-based patterns: exposed DB, exposed admin, open SSH, default creds), auto-queue follow-up tasks on critical match |
| x | OSINTote-2yq.6 | AI query engine — NL→DSL→SQL pipeline, DSL parser/generator, AI intent extraction, SQL translation from DSL, result formatting with natural language summary, /api/ai/query endpoint |
| x | OSINTote-2yq.8 | AI analysis engine — post-task async analysis, structured output (risk_score, summary, findings array with severity/evidence/recommendation, missing_data), markdown + JSON metadata, CLI: osintote analyze |

## Polish & Ship (35e) � COMPLETE

| Status | ID | Description |
|--------|----|-------------|
| x | OSINTote-35e | Epic: Polish & Ship — settings, keys UI, notifications, error handling, logging, documentation, Docker, CI/CD, packaging |
| x | OSINTote-35e.12 | Docker image publishing — ghcr.io registry, tag-based release workflow (v* triggers), docker/build-push-action, multi-arch build (linux/amd64 + linux/arm64), latest tag on main |
| x | OSINTote-35e.11 | Pre-commit & lint integration — ruff (lint + format, --fix), mypy (--ignore-missing-imports), pre-commit-hooks (trailing-whitespace, end-of-file, check-yaml, check-added-large-files), ruff pre-commit rev v0.9.0, mypy rev v1.14 |
| x | OSINTote-35e.10 | PyPI packaging — hatch build backend, version management (osintote/__version__.py), pyproject.toml dependencies lock, pip installable with all requirements, entry points (osintote CLI command) |
| x | OSINTote-35e.9 | Testing infrastructure — unit tests (engine logic, models, crypto, report gen), integration tests (FastAPI test client + SQLite, mocked external APIs), scenario fixtures (Faker deterministic seed), pytest-httpx for HTTP mocking, coverage --cov=osintote 80% threshold |
| x | OSINTote-35e.8 | Docker multi-stage build — Stage 1: Node frontend build, Stage 2: Python backend + copied frontend build, EXPOSE 8000, CMD uvicorn, docker-compose.yml with named volume for SQLite, OSINTOTE_LISTEN_HOST env |
| x | OSINTote-35e.7 | Callback system — Notifier.run_command(), CLI --on-complete flag, safe shell execution (no eval, explicit command parsing), webhook execution for on_task_complete events |
| x | OSINTote-35e.6 | Final integration & demo — end-to-end test: target → DNS → HTTP → results → report, full CLI + web UI flow, screenshot documentation, release checklist, CHANGELOG.md v0.1.0 |
| x | OSINTote-35e.4 | Settings management UI — /settings page, AI config editor (provider, models per role), default recipe selector, output format picker, theme toggle, persistence via localStorage + server sync |
| x | OSINTote-35e.5 | Documentation — README (description, install, quick start, features, screenshots), getting-started.md, cli-reference.md, web-ui-guide.md, api-reference.md (auto-generated), recipes/built-in.md, recipes/custom.md, security.md, faq.md, ADR/001-005 |
| x | OSINTote-35e.3 | Keys management UI — /settings page → keys tab, add/edit/delete API keys with name/source, status display (active/rate-limited/failed), primary/fallback indicator, encrypted display masking |
| x | OSINTote-35e.2 | Desktop notifications — cross-platform notifier (osascript macOS, notify-send Linux, Toast Windows), CLI --notify flag, web UI browser Notification API, osintote settings set notifications true |
| x | OSINTote-35e.1 | Logging UI — /logs page (collapsible tab), SSE log stream with color-coded severity, search/filter by task/logger/level, auto-scroll, clear button, export log |

## Foundation (enz) � COMPLETE

| Status | ID | Description |
|--------|----|-------------|
| x | OSINTote-enz | Epic: Foundation — project structure, SQLite schema, Alembic, encryption, CLI skeleton, init, serve |
| x | OSINTote-enz.8 | SQLite schema & Alembic — 8 tables (targets, records, tasks, api_keys, settings, relationships, errors, webhooks), strategic indices, auto-migrate on startup |
| x | OSINTote-enz.7 | Encryption module — AES-256 key storage, PBKDF2 master password derivation, crypto.py, osintote init flow (master password → encrypted DB) |
| x | OSINTote-enz.5 | CLI skeleton — typer commands (init, serve, status), osintote/__init__.py, package entry points, --help auto-docs |
| x | OSINTote-enz.6 | Logging infrastructure — structured JSON logger (timestamp, level, logger, task_id, stage, message, meta), file + console + SSE stream output, .osintote/logs/ rotation |
| x | OSINTote-enz.4 | CI/CD scaffolding — GitHub Actions (pytest, mypy, ruff, npm build, Docker build), pre-commit hooks (ruff, mypy, trailing-whitespace, check-yaml), coverage threshold 80% |
| x | OSINTote-enz.3 | SQLModel ORM models — Target, Record, Task, ApiKey, Setting, Relationship, Error, Webhook with SQLAlchemy 2.0 async, pydantic schemas |
| x | OSINTote-enz.2 | Engine config — per-source Pydantic BaseSettings (ShodanConfig, CensysConfig, etc.), env var prefix support, CLI flag override, EngineConfig aggregator |
| x | OSINTote-enz.1 | Project scaffolding — monolithic osintote/ package + frontend/ sibling, pyproject.toml (hatch), Makefile + uv dev workflow, .gitignore, .editorconfig |

## Data Sources & Intelligence (jcz) � COMPLETE

| Status | ID | Description |
|--------|----|-------------|
| x | OSINTote-jcz | Epic: Data Sources — DNS, HTTP probe, WHOIS, CLI wrappers, API sources, rate limiting, key management |
| x | OSINTote-jcz.12 | Shodan API source — httpx API calls, rate limiting (1 req/s default), circuit breaker (3 failures = 5min cooldown), fallback detection |
| x | OSINTote-jcz.11 | WHOIS stage — python-whois wrapper, domain registration info extraction, name server listing, contact data |
| x | OSINTote-jcz.10 | Rate limiter — per-source asyncio semaphore, adaptive backoff (429 detection → halve rate → exponential recovery), per-key rate limits |
| x | OSINTote-jcz.8 | API key management — encrypted storage (AES-256 in SQLite), primary/fallback key rotation, CLI add/remove/list, UI status display |
| x | OSINTote-jcz.9 | Target normalization & dedup — TargetNormalizer (lowercase, strip dots, IP compression), relationship linking (hosts, resolves_to, ptr), canonical target resolution |
| x | OSINTote-jcz.7 | nuclei wrapper — vulnerability scanning (severity filter, template selection), JSONL output parsing, CVE normalization |
| x | OSINTote-jcz.5 | CLI wrapper framework — async subprocess (asyncio.create_subprocess_exec), timeouts, resource limits (memory/CPU), no shell=True, working dir isolation, env isolation |
| x | OSINTote-jcz.6 | subfinder wrapper — subdomain enumeration via passive sources, output file parsing, dedup against built-in results |
| x | OSINTote-jcz.4 | VirusTotal API source — httpx API calls, rate limiting (4/min), malware detection, IP/domain reputation lookup |
| x | OSINTote-jcz.3 | HTTP probing stage — httpx alive host discovery, concurrency config, timeout, status code filtering, response headers capture |
| x | OSINTote-jcz.2 | nmap wrapper — port scanning (-Pn -sV -T timing -p ports), XML output parsing, result normalization to records |
| x | OSINTote-jcz.1 | DNS enumeration stage — built-in dnspython resolver + subfinder CLI wrapper, recursive enumeration, max depth config, result normalization |

## Pipeline & Engine (yk2) � COMPLETE

| Status | ID | Description |
|--------|----|-------------|
| x | OSINTote-yk2 | Epic: Pipeline & Engine — task engine, recipe system, executor, SSE progress, task lifecycle, web UI basics |
| x | OSINTote-yk2.12 | CLI progress display — rich terminal output (live progress bars, colored findings with ✓/!/✗, scrollable log, summary panel), osintote recon command |
| x | OSINTote-yk2.11 | Error handling framework — severity tiers (info→toast, warning→toast+banner, error→banner+log, critical→banner+log+notification), Error model, /api/logs SSE |
| x | OSINTote-yk2.10 | Recipe system — JSON recipe config (name, description, stages array), bundled defaults in osintote/recipes/, user overrides in .osintote/recipes/, depends_on ordering |
| x | OSINTote-yk2.8 | Write-ahead log — WriteAhead buffer class, periodic checkpoint (5s), crash recovery, background checkpoint task, DB always has latest snapshot |
| x | OSINTote-yk2.9 | Target management UI — /targets page, add/list/remove/show forms, left panel target list, shadcn/svelte components (data table, dialogs, badges) |
| x | OSINTote-yk2.7 | Web UI shell — SvelteKit 2.61.1 project setup (npm 22), 3-panel layout (left: targets, center: tasks, right: details), tab navigation, lazy-loaded route modules |
| x | OSINTote-yk2.6 | Results table UI — /results page (right panel), filterable/sortable data table, clickable rows, detail panel expansion, record type icons |
| x | OSINTote-yk2.4 | SSE progress streaming — /api/tasks/{id}/events endpoint, event types (task_started, progress, stage_complete, task_finished), EventSource API on client |
| x | OSINTote-yk2.5 | Task pipeline UI — /tasks page, task list with status indicators (green/yellow/red), progress bars, quick actions (start/cancel/resume/delete), SSE live updates |
| x | OSINTote-yk2.3 | Task lifecycle API — task create/start/cancel/resume/delete, status transitions (pending→running→completed/failed/cancelled), API routes + CLI commands |
| x | OSINTote-yk2.2 | Executor engine — asyncio event loop (I/O pool), process pool (CPU-bound), priority queue, task dispatch by cost (light/medium/heavy), worker management |
| x | OSINTote-yk2.1 | Stage strategy pattern — Stage ABC protocol (execute method), StageContext dataclass, StageResult dataclass, STAGE_REGISTRY dict, per-stage testability |
