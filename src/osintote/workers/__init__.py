# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Workers package — OSINT data source implementations.

Auto-discovers and registers stage implementations:
    - http_probe: HTTP alive host discovery
    - nmap: port scanning
    - subfinder: subdomain enumeration
    - nuclei: vulnerability scanning
    - normalizer: target normalisation & deduplication
    - dns_enumeration: DNS record enumeration (A/AAAA/MX/NS/TXT/SOA)
    - whois: WHOIS domain registration info
    - virustotal: VirusTotal threat intelligence API
    - shodan: Shodan network recon API
"""

from osintote.workers import (
    dns_enumeration,
    http_probe,
    nmap,
    normalizer,
    nuclei,
    shodan,
    subfinder,
    virustotal,
    whois,
)

# Auto-register all stages
nmap.__register__()
nuclei.__register__()
subfinder.__register__()
dns_enumeration.__register__()
whois.__register__()
virustotal.__register__()
shodan.__register__()

__all__ = [
    "dns_enumeration",
    "http_probe",
    "nmap",
    "normalizer",
    "nuclei",
    "shodan",
    "subfinder",
    "virustotal",
    "whois",
]
