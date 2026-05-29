# OSINTOTE — Project Status Map

> Last updated: 2026-05-29

## Summary

```
OVERALL  [+++++++++++++++++++++++++++++++++++++++++++++++++-------------]  41/57 (72%) | 16 remaining | 0 blocked
```

| Epic | Status | Done/Total | % |
|------|--------|-----------|---|
| **Foundation (enz)** | COMPLETE | 8/8 | 100% |
| **Pipeline & Engine (yk2)** | COMPLETE | 12/12 | 100% |
| **Polish & Ship (35e)** | IN PROGRESS | 12/13 | 92% |
| **Data Sources (jcz)** | IN PROGRESS | 2/13 | 15% |
| **Intelligence & AI (2yq)** | IN PROGRESS | 1/9 | 11% |

---

## Foundation (enz) — COMPLETE ✓

| Status | ID | Description |
|--------|----|-------------|
| ✓ | OSINTote-enz | Epic: Foundation — project structure, SQLite schema, Alembic, encryption |
| ✓ | OSINTote-enz.1 | Project scaffolding — monolithic osintote/ package + frontend/ sibling, Makefile, .editorconfig, uv.lock |
| ✓ | OSINTote-enz.2 | Engine config — per-source Pydantic BaseSettings (ShodanConfig, CensysConfig, etc.) |
| ✓ | OSINTote-enz.3 | SQLModel ORM models — Target, Record, Task, ApiKey, Setting, Relationship, Error, Log |
| ✓ | OSINTote-enz.4 | CI/CD scaffolding — GitHub Actions (pytest, mypy, ruff, npm build, Docker), pre-commit hooks |
| ✓ | OSINTote-enz.5 | CLI skeleton — typer commands (init, serve, status), osintote/__init__, __version__ |
| ✓ | OSINTote-enz.6 | Logging infrastructure — structured JSON logger (timestamp, level, logger, message, pid, task_id), SSELogHandler |
| ✓ | OSINTote-enz.7 | Encryption module — AES-256-GCM key storage, PBKDF2 master password derivation, KeyStorage |
| ✓ | OSINTote-enz.8 | SQLite schema & Alembic — 8 tables (targets, records, tasks, api_keys, settings, relationships, errors, logs), 8 migration files |

---

## Pipeline & Engine (yk2) — COMPLETE ✓

| Status | ID | Description |
|--------|----|-------------|
| ✓ | OSINTote-yk2 | Epic: Pipeline & Engine — task engine, recipe system, executor, SSE progress, task lifecycle, Web UI basics |
| ✓ | OSINTote-yk2.1 | Stage strategy pattern — Stage ABC protocol (execute method), StageContext, StageResult, STAGE_REGISTRY decorator, FakeStage |
| ✓ | OSINTote-yk2.2 | Executor engine — asyncio event loop (I/O pool), process pool (CPU-bound), cost-based dispatch (light/medium/heavy), SSE streaming |
| ✓ | OSINTote-yk2.3 | Task lifecycle API — task create/start/cancel/resume/delete, status transitions (pending→running→completed/failed/cancelled), API routes + CLI commands |
| ✓ | OSINTote-yk2.4 | SSE progress streaming — /api/tasks/{id}/stream endpoint, event types (task_started, progress, stage_complete, task_finished), SSEStream.svelte component |
| ✓ | OSINTote-yk2.5 | Task pipeline UI — /tasks page, task list with status indicators (green/blue/yellow/red), progress bars, TaskDialog, TaskDetail |
| ✓ | OSINTote-yk2.6 | Results table UI — /results page (right panel), filterable/sortable table, severity/type filtering, ResultRow/ResultDetail |
| ✓ | OSINTote-yk2.7 | Web UI shell — SvelteKit 2.61.1 project setup, dark OSINT theme (GitHub Dark), 3-panel layout (nav/sidebar/content), Panel/TabNav components |
| ✓ | OSINTote-yk2.9 | Target management UI — /targets page, add/list/remove/show forms, lazy-loaded routes, TargetDialog/TargetDetail |
| ✓ | OSINTote-yk2.8 | Write-ahead log — WriteAhead buffer class, periodic checkpoint (5s), crash recovery |
| ✓ | OSINTote-yk2.10 | Recipe system — JSON recipe config (name, description, stages array), bundled defaults (quick-scan, full-scan, passive-only), topological sorting, CLI commands |
| ✓ | OSINTote-yk2.11 | Error handling framework — severity tiers (info→toast, warning→toast+banner, error→banner+log, critical→banner+log+notif), Error model, /api/errors, SSE error stream |
| ✓ | OSINTote-yk2.12 | CLI progress display — rich terminal output (live progress bars, colored findings ✓/!/✗, scrollable log, summary panel), integrated with Executor engine |

---

## Polish & Ship (35e) — 11/13 (84%)

| Status | ID | Description |
|--------|----|-------------|
| **o** | OSINTote-35e | Epic: Polish & Ship — settings, keys UI, notifications, error handling, packaging, docs, Docker |
| ✓ | OSINTote-35e.1 | Logging UI — /logs page (collapsible tab), SSE log stream with color-coded severity, real-time filtering |
| ✓ | OSINTote-35e.2 | Desktop notifications — cross-platform notifier (osascript macOS, msgbox Windows, notify-send Linux), BrowserNotifier |
| ✓ | OSINTote-35e.3 | Keys management UI — /settings page → keys tab, add/edit/delete API keys, status indicators (active/rate-limited/failed), encrypted masking |
| ✓ | OSINTote-35e.4 | Settings management UI — /settings page, AI config editor (provider, models per role), default recipe selector, output format picker (JSON/Markdown/HTML), theme toggle |
| ✓ | OSINTote-35e.5 | Documentation — README, getting-started, cli-reference, web-ui-guide, security, faq, api-reference, recipes, 5 ADRs |
| ✓ | OSINTote-35e.6 | Final integration & demo — comprehensive E2E test (target → DNS → HTTP → results → report, WAL verification, report generation, API routes), reporter.py db fix, CHANGELOG.md v0.1.0 |
| ✓ | OSINTote-35e.7 | Callback system — Notifier.run_command(), CLI --on-complete flag, safe shell execution (shlex + subprocess_exec), HMAC-SHA256 webhook signing |
| ✓ | OSINTote-35e.8 | Docker multi-stage build — Stage 1: Node frontend build, Stage 2: Python FastAPI (uvicorn + gunicorn) |
| ✓ | OSINTote-35e.9 | Testing infrastructure — unit tests (engine logic, models, crypto, router, CLI, database, API), integration tests (route registration, health endpoint, DB setup) |
| ✓ | OSINTote-35e.10 | PyPI packaging — hatch build backend, version management (osintote/_version__.py), sdist + wheel verification, excluded tests from wheel |
| ✓ | OSINTote-35e.11 | Pre-commit & lint integration — ruff (lint + format, --fix), mypy (type checking), GitHub Actions CI gates |
| ✓ | OSINTote-35e.12 | Docker image publishing — ghcr.io registry, tag-based release workflow, multi-arch (amd64 + arm64) |

---

## Data Sources (jcz) — 2/13 (15%)

| Status | ID | Description |
|--------|----|-------------|
| **o** | OSINTote-jcz | Epic: Data Sources — DNS, HTTP probe, WHOIS, CLI wrappers, API sources |
| **o** | OSINTote-jcz.1 | DNS enumeration stage — built-in dnspython resolver + subfinder CLI wrapper |
| **o** | OSINTote-jcz.2 | nmap wrapper — port scanning (-Pn -sV -T timing -p ports), XML output, async subprocess |
| ✓ | OSINTote-jcz.3 | HTTP probing stage — httpx alive host discovery, timeout, status code filtering, response headers capture (server, CSP, HSTS, content-type) |
| **o** | OSINTote-jcz.4 | VirusTotal API source — httpx API calls, rate limiting (4/min), malware classification |
| ✓ | OSINTote-jcz.5 | CLI wrapper framework — SubprocessRunner (asyncio.create_subprocess_exec, no shell=True), timeouts, memory/CPU limits, work dir isolation, env isolation, run/run_safe API, 19 unit tests |
| **o** | OSINTote-jcz.6 | subfinder wrapper — subdomain enumeration via passive sources, output parsing |
| **o** | OSINTote-jcz.7 | nuclei wrapper — vulnerability scanning (severity filter, template selection) |
| **o** | OSINTote-jcz.8 | API key management — encrypted storage (AES-256 in SQLite), primary/fallback selection, usage tracking |
| **o** | OSINTote-jcz.9 | Target normalization & dedup — TargetNormalizer (lowercase, strip www, remove trailing dot) |
| **o** | OSINTote-jcz.10 | Rate limiter — per-source asyncio semaphore, adaptive backoff (429 detection, exponential retry) |
| **o** | OSINTote-jcz.11 | WHOIS stage — python-whois wrapper, domain registration info extraction |
| **o** | OSINTote-jcz.12 | Shodan API source — httpx API calls, rate limiting (1 req/s default), banner parsing |

---

## Intelligence & AI (2yq) — 0/9 (0%)

| Status | ID | Description |
|--------|----|-------------|
| **o** | OSINTote-2yq | Epic: Intelligence & AI — AI integration, context pruning, report generation, graph, natural language query |
| **o** | OSINTote-2yq.1 | AI provider abstraction — AIProvider interface (analyze/query/suggest methods), OpenAICompatibleHTTP base class, provider-specific extensions (Ollama, LMStudio, llama.cpp, vLLM), auto-discovery via /v1/models |
| **o** | OSINTote-2yq.2 | Webhook system — Webhook model, configurable endpoints (/api/webhook/{source}), HMAC-SHA256 verification |
| ✓ | OSINTote-2yq.3 | Report generation service — Reporter service, JSON export (structured with summary), Markdown export (tables/summary/risk score), HTML export (vis.js network, search/filter, print CSS) |
| **o** | OSINTote-2yq.4 | Relationship graph — vis.js Network with custom theming (node colors by type: IP=blue, domain=green, vuln=red, port=yellow), edge labels, zoom/pan, click-to-select |
| **o** | OSINTote-2yq.5 | AI workflow suggestions — post-task recommendations list, critical findings alert, /api/suggest/{task_id} endpoint |
| **o** | OSINTote-2yq.6 | AI query engine — NL→DSL→SQL pipeline, DSL parser/generator, AI intent extraction, SQL translation from DSL, result formatting with natural language summary, /api/ai/query endpoint |
| **o** | OSINTote-2yq.7 | Context pruning system — auto-summarizer (rule-based stats: domain count, IP count, port count, vuln count), smart context builder (executive summary, top findings, infrastructure, threat intel), token limits (~5K context) |
| **o** | OSINTote-2yq.8 | AI analysis engine — post-task async analysis, structured output (risk score, recommendations, IOC extraction) |

---

## Key Dependencies

```
35e.6 (Final Integration) ─── blocked by ──► yk2.3 ✓, yk2.7 ✓, yk2.8 ✓, yk2.10 ✓, yk2.11 ✓, yk2.12 ✓, jcz.3 ✓, 2yq.3 ✓, enz.5 ✓
2yq.1 (AI Provider) ─── blocked by ──► enz.1 ✓
```

## Recommended Next Steps

1. **35e.6** (Final Integration) — ✓ COMPLETE. E2E test, CHANGELOG v0.1.0, reporter fix.
2. **jcz.5** (CLI wrapper framework) — ✓ COMPLETE. SubprocessRunner for safe async CLI execution.
3. **jcz.2** (nmap wrapper) — unblocked by jcz.5, uses CLI wrapper framework
4. **jcz.6** (subfinder wrapper) — unblocked by jcz.5
5. **jcz.7** (nuclei wrapper) — unblocked by jcz.5
3. **jcz.9** (Target normalization) — unblocks jcz.1, jcz.3, 2yq.4
4. **jcz.1** (DNS enumeration) — first concrete data source
5. **2yq.8** (AI analysis) — requires 2yq.7 (context pruning) first

## Test Status

- **354 tests passing**, 2 skipped, 2 warnings
- Coverage across: engine (executor, stage, wal), CLI, API, crypto, logging, database, ORM, notifier, platform_notifiers, SSE streaming, HTTP probe, error handling, recipes, reports, recon display

## Code Quality

- ✅ All pre-commit hooks pass (ruff format, ruff lint, mypy, trailing whitespace, end of file)
- ✅ Build passes: `uv run pytest`, `npm run build`, `uv run mypy` all clean
