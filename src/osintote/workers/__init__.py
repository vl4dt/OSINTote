# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Workers package — OSINT data source implementations.

Auto-discovers and registers stage implementations:
    - http_probe: HTTP alive host discovery
    - nmap: port scanning
    - subfinder: subdomain enumeration
    - nuclei: vulnerability scanning
    - normalizer: target normalisation & deduplication
"""

from osintote.workers import http_probe, nmap, normalizer, nuclei, subfinder

# Auto-register all stages
nmap.__register__()
nuclei.__register__()
subfinder.__register__()

__all__ = ["http_probe", "nmap", "normalizer", "nuclei", "subfinder"]
