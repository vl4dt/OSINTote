# Web UI Guide

Complete walkthrough of the OSINTote web interface.

## Overview

The Web UI provides a dark-themed, 3-panel interface for OSINT operations:

| Panel | Description |
|-------|-------------|
| **Sidebar** | Navigation menu with dashboard, targets, tasks, results, logs, and settings |
| **Main Content** | Data views, forms, and interactive elements |
| **Details** | Contextual details for selected items (right panel) |

### Theme

The UI uses a GitHub Dark-inspired theme:

- Dark backgrounds (`#0d1117`, `#161b22`, `#21262d`)
- Subtle borders (`#30363d`)
- Monospace font (Fira Mono) for technical data
- Status color coding

## Pages

### Dashboard

The home page shows a real-time overview:

- **Active Tasks** — Count of running tasks with status badges
- **Total Targets** — Number of managed intelligence targets
- **Recent Results** — Latest collected records with severity indicators
- **Live Clock** — Real-time system clock with AM/PM toggle

### Targets

Manage intelligence targets:

- **Search & Filter** — Find targets by name, type (domain, IP, URL)
- **Add Target** — Dialog form for new targets with type selection
- **Target Cards** — Visual cards showing target details and record counts
- **Detail View** — Expanded view with all associated records and relationships

#### Adding a Target

1. Click **"+ Add Target"**
2. Enter a name (e.g., `example.com`)
3. Select the type (Domain, IP Address, URL, Email, Custom)
4. Click **Create**

#### Target Details

Click on any target card to view:
- All collected records
- Target type and metadata
- Associated tasks
- Relationship links

### Tasks

Run and monitor reconnaissance pipelines:

- **Quick Actions** — Start new tasks directly from the dashboard
- **Task Cards** — Visual cards with progress bars and status badges
- **Live Progress** — SSE-powered real-time task progress updates
- **Task Details** — Expandable view showing stages, results, and metadata

#### Starting a Task

1. Go to the **Tasks** page
2. Click **"+ New Task"**
3. Select a target and recipe
4. Click **Start**

#### Task Status Indicators

| Status | Color | Description |
|--------|-------|-------------|
| **Pending** | Yellow | Task created, waiting to start |
| **Running** | Blue | Task is executing |
| **Completed** | Green | Task finished successfully |
| **Failed** | Red | Task encountered an error |
| **Cancelled** | Grey | Task was cancelled |

### Results

View and analyze collected intelligence:

- **Filter Panel** — Filter by severity (Critical, High, Medium, Low, Info) and type
- **Result Rows** — Expandable rows showing source, data, and confidence scores
- **Detail View** — Full record details with JSON data viewer

#### Severity Colors

| Severity | Color |
|----------|-------|
| Critical | Red (`#f85149`) |
| High | Orange (`#d29922`) |
| Medium | Yellow (`#e3b341`) |
| Low | Green (`#3fb950`) |
| Info | Blue (`#58a6ff`) |

### Logs

Real-time log monitoring with SSE streaming:

- **Live Stream** — Connects to `/api/logs/stream` via Server-Sent Events
- **Severity Filter** — Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Logger Filter** — Filter by logger name
- **Search** — Full-text search across log messages
- **Auto-Scroll** — Automatically scroll to latest entries
- **Export** — Download logs as JSON
- **Collapse/Expand** — Toggle the log panel visibility

#### Severity Colors

| Level | Color |
|-------|-------|
| DEBUG | `#6e7681` (grey) |
| INFO | `#58a6ff` (blue) |
| WARNING | `#d29922` (orange) |
| ERROR | `#f85149` (red) |
| CRITICAL | `#da3633` (dark red) |

### Settings

Project configuration and management:

- **AI Configuration** — Configure AI providers (OpenAI, Ollama, LMStudio, vLLM)
  - Provider type selection
  - Model names and API endpoints
  - Enable/disable AI features
- **Default Recipe** — Select the default recipe for new recon tasks
- **Output Format** — Choose the default report format (JSON, Markdown, HTML)
- **Theme Toggle** — Switch between dark/light theme (future)

#### API Keys

Manage API keys for external OSINT sources:

- **Add Key** — Create a new encrypted API key entry
- **Edit Key** — Modify key details (name, source, target association)
- **Delete Key** — Remove a key (requires confirmation)
- **Rotate Primary** — Change the primary key for a source
- **Status Indicators** — Primary, fallback, and inactive status badges
- **Masked Display** — Keys are displayed with partial masking for security

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Focus search bar |
| `Esc` | Close dialogs / clear filters |
| `N` | New task (from any page) |

## Navigation

The sidebar provides quick navigation between all pages:

```
Dashboard → Home overview
Targets   → Target management
Tasks     → Task lifecycle and monitoring
Results   → Collected intelligence
Logs      → Real-time log streaming
Settings  → Configuration and API keys
```

## Browser Support

The Web UI is tested on:

- Chrome / Chromium (latest)
- Firefox (latest)
- Edge (latest)

SSE (Server-Sent Events) requires a modern browser with `EventSource` support.
