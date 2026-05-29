# Web UI Guide

Complete walkthrough of the OSINTote web interface.

## Overview

The Web UI provides a dark-themed, 3-panel interface for OSINT operations:

| Panel | Description |
|-------|-------------|
| **Sidebar** | Navigation menu with dashboard, targets, tasks, and results |
| **Main Content** | Data views, forms, and interactive elements |
| **Details** | Contextual details for selected items |

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

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Focus search bar |
| `Esc` | Close dialogs / clear filters |
| `N` | New task (from any page) |

## Theming

The UI uses a GitHub Dark-inspired theme with:

- Dark backgrounds (`#0d1117`, `#161b22`, `#21262d`)
- Subtle borders (`#30363d`)
- Monospace font (Fira Mono) for technical data
- Status color coding
