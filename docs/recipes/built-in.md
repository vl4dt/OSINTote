# Built-in Recipes

Pre-built reconnaissance pipelines for common OSINT workflows.

## Overview

Recipes define ordered lists of stages to execute against a target. Each recipe is designed for a specific reconnaissance objective. Stages execute in topological order based on `depends_on` relationships.

### Available Recipes

| Recipe | Description | Stages |
|--------|-------------|--------|
| `quick-scan` | Quick reconnaissance: DNS + HTTP probe | DNS, HTTP probe |
| `full-scan` | Comprehensive investigation: DNS → HTTP → nmap → nuclei | DNS, HTTP probe, nmap, nuclei |
| `passive-only` | Passive reconnaissance only: DNS + WHOIS | DNS, WHOIS |

## Recipe: quick-scan

**Use case**: Standard reconnaissance for a new target.

**Stages**:

1. **`dns-enumerate`** — Resolve hostname, get A/AAAA/MX/NS/TXT/SOA records (dnspython + subfinder)
2. **`http-probe`** — Check HTTP/HTTPS services, capture response headers (server, CSP, HSTS, content-type)

**Expected output**: DNS records, HTTP headers, status codes, discovered subdomains

## Recipe: full-scan

**Use case**: Deep investigation of a target domain.

**Stages**:

1. **`dns-enumerate`** — DNS record enumeration
2. **`http-probe`** — HTTP service discovery
3. **`nmap`** — Port scanning (-Pn -sV -T timing -p ports) and service detection
4. **`nuclei`** — Vulnerability scanning with severity filtering

**Expected output**: DNS records, HTTP headers, open ports, service versions, CVE findings, vulnerabilities

## Recipe: passive-only

**Use case**: Non-intrusive intelligence gathering.

**Stages**:

1. **`dns-enumerate`** — DNS record enumeration
2. **`whois`** — Domain registration and contact information extraction

**Expected output**: DNS records, WHOIS data (registrar, creation date, name servers)

## Stage Names Reference

| Stage Name | Description | External Tool Required |
|------------|-------------|----------------------|
| `dns-enumerate` | DNS record enumeration | dnspython (built-in), subfinder (optional) |
| `http-probe` | HTTP alive host discovery | None (uses httpx) |
| `nmap` | Port scanning and service detection | `nmap` |
| `nuclei` | Template-based vulnerability scanning | `nuclei` |
| `whois` | Domain registration info | `python-whois` |

## Recipe Storage

- **Bundled defaults** are loaded from `osintote/recipes/models.py` (`DEFAULT_RECIPES`)
- **User overrides** are stored in `.osintote/recipes/*.json` and take precedence

## Next Steps

- See [Custom Recipes](custom.md) for writing and registering custom recipes
- See [Recipes](../cli-reference.md#osintote-recipes) for CLI commands
