# Built-in Recipes

Pre-built reconnaissance pipelines for common OSINT workflows.

## Overview

Recipes define ordered lists of stages to execute against a target. Each recipe is designed for a specific reconnaissance objective.

### Available Recipes

| Recipe | Description | Stages |
|--------|-------------|--------|
| `basic` | Essential reconnaissance | DNS, HTTP probe |
| `full` | Comprehensive investigation | DNS, HTTP probe, WHOIS |
| `quick` | Fast overview | DNS only |

## Recipe: Basic

**Use case**: Standard reconnaissance for a new target.

**Stages**:
1. **DNS** — Resolve hostname, get records
2. **HTTP Probe** — Check HTTP/HTTPS service, get headers

**Expected output**: DNS records, HTTP headers, status codes

## Recipe: Full

**Use case**: Deep investigation of a target domain.

**Stages**:
1. **DNS** — Resolve hostname, get records
2. **HTTP Probe** — Check HTTP/HTTPS service
3. **WHOIS** — Get registration and contact information

**Expected output**: DNS records, HTTP headers, WHOIS data

## Recipe: Quick

**Use case**: Rapid triage of many targets.

**Stages**:
1. **DNS** — Resolve hostname

**Expected output**: DNS records only

## Adding Recipes

New recipes can be defined in the engine configuration or via the API. See [Custom Recipes](custom.md) for details.
