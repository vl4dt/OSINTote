"""Per-source engine configuration using Pydantic BaseSettings.

All settings read from environment variables prefixed with ``OSINTOTE_``,
and can be overridden by CLI flags when the ``EngineConfig`` is merged with
user-provided overrides.

Each source has its own typed config so that runtime look-up is type-safe
and self-documenting::

    from osintote.engine.config import EngineConfig, ShodanConfig

    config = EngineConfig.load()
    api_key = config.shodan.api_key  # str | None
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── generic helpers ──────────────────────────────────────────────────


class BaseConfig(BaseSettings):
    """Base class for every per-source configuration.

    Subclasses must set ``env_prefix`` to their own namespace
    (e.g. ``OSINTOTE_SHODAN_``).  No nested delimiter — flat naming.
    """

    model_config = SettingsConfigDict(env_prefix="", env_nested_delimiter="")

    enabled: bool = Field(
        default=True,
        description="Whether this source is active.",
    )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


# ── intelligence API sources ─────────────────────────────────────────


class ShodanConfig(BaseConfig):
    """Shodan Internet Scanner configuration."""

    model_config = SettingsConfigDict(env_prefix="OSINTOTE_SHODAN_")

    api_key: SecretStr | None = Field(
        default=None,
        description="Shodan API key (OSINTOTE_SHODAN_API_KEY).",
    )
    rate_limit: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Maximum requests per second (Shodan default 1 req/s).",
    )
    cooldown_minutes: int = Field(
        default=5,
        description="Cooldown minutes after circuit-breaker trip (3 consecutive failures).",
    )

    @field_validator("api_key")
    @classmethod
    def _reject_empty_key(cls, v: SecretStr | None) -> SecretStr | None:
        if v is not None and not v.get_secret_value().strip():
            raise ValueError("OSINTOTE_SHODAN_API_KEY must not be empty")
        return v


class CensysConfig(BaseConfig):
    """Censys Explorer configuration."""

    model_config = SettingsConfigDict(env_prefix="OSINTOTE_CENSYS_")

    api_key: SecretStr | None = Field(
        default=None,
        description="Censys API key (OSINTOTE_CENSYS_API_KEY).",
    )
    api_secret: SecretStr | None = Field(
        default=None,
        description="Censys API secret (OSINTOTE_CENSYS_API_SECRET).",
    )
    rate_limit: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum requests per second (Censys default 5 req/s for paid).",
    )

    @field_validator("api_key")
    @classmethod
    def _reject_empty_key(cls, v: SecretStr | None) -> SecretStr | None:
        if v is not None and not v.get_secret_value().strip():
            raise ValueError("OSINTOTE_CENSYS_API_KEY must not be empty")
        return v

    @field_validator("api_secret")
    @classmethod
    def _reject_empty_secret(cls, v: SecretStr | None) -> SecretStr | None:
        if v is not None and not v.get_secret_value().strip():
            raise ValueError("OSINTOTE_CENSYS_API_SECRET must not be empty")
        return v


class VirusTotalConfig(BaseConfig):
    """VirusTotal Intelligence configuration."""

    model_config = SettingsConfigDict(env_prefix="OSINTOTE_VT_")

    api_key: SecretStr | None = Field(
        default=None,
        description="VirusTotal API key (OSINTOTE_VT_API_KEY).",
    )
    rate_limit: int = Field(
        default=4,
        ge=1,
        le=120,
        description="Maximum requests per minute (VT free = 4/min, paid = 1/sec).",
    )

    @field_validator("api_key")
    @classmethod
    def _reject_empty_key(cls, v: SecretStr | None) -> SecretStr | None:
        if v is not None and not v.get_secret_value().strip():
            raise ValueError("OSINTOTE_VT_API_KEY must not be empty")
        return v


# ── CLI / tool wrappers ──────────────────────────────────────────────


class NmapConfig(BaseConfig):
    """Nmap port scanner configuration."""

    model_config = SettingsConfigDict(env_prefix="OSINTOTE_NMAP_")

    binary_path: str = Field(
        default="nmap",
        description="Path to the nmap binary.",
    )
    timeout: int = Field(
        default=300,
        ge=10,
        description="Per-host scan timeout in seconds.",
    )
    scan_type: Literal["-Pn", "-sP", "-sS", "-sT"] = Field(
        default="-Pn",
        description="Default scan type: -Pn (no ping), -sP (ping only), -sS (SYN), -sT (TCP).",
    )
    service_detection: bool = Field(
        default=True,
        description="Enable version/service detection (-sV).",
    )
    timing: Literal["T0", "T1", "T2", "T3", "T4", "T5"] = Field(
        default="T3",
        description="Timing template (T0=paranoid, T5=insane).",
    )
    max_hosts: int = Field(
        default=1000,
        ge=1,
        description="Maximum number of hosts to scan in a single run.",
    )


class SubfinderConfig(BaseConfig):
    """Subfinder subdomain enumeration configuration."""

    model_config = SettingsConfigDict(env_prefix="OSINTOTE_SUBFINDER_")

    binary_path: str = Field(
        default="subfinder",
        description="Path to the subfinder binary.",
    )
    rate_limit: int = Field(
        default=0,
        ge=0,
        description="Rate limit (0 = unlimited, uses passive sources).",
    )


class NucleiConfig(BaseConfig):
    """Nuclei vulnerability scanner configuration."""

    model_config = SettingsConfigDict(env_prefix="OSINTOTE_NUCLEI_")

    binary_path: str = Field(
        default="nuclei",
        description="Path to the nuclei binary.",
    )
    timeout: int = Field(
        default=120,
        ge=10,
        description="Per-request timeout in seconds.",
    )
    severity: list[Literal["info", "low", "medium", "high", "critical"]] = Field(
        default=["info", "low", "medium", "high", "critical"],
        description="Severity levels to include.",
    )
    rate_limit: int = Field(
        default=0,
        ge=0,
        description="Rate limit per second (0 = unlimited, nuclei default 150/s).",
    )
    templates: str = Field(
        default="",
        description="Path to custom nuclei template directory.",
    )


class WhoisConfig(BaseConfig):
    """WHOIS lookup configuration."""

    model_config = SettingsConfigDict(env_prefix="OSINTOTE_WHOIS_")

    timeout: int = Field(
        default=10,
        ge=1,
        description="Per-query timeout in seconds.",
    )


# ── built-in stages ──────────────────────────────────────────────────


class DNSConfig(BaseConfig):
    """Built-in DNS enumeration configuration."""

    model_config = SettingsConfigDict(env_prefix="OSINTOTE_DNS_")

    resolver_timeout: int = Field(
        default=5,
        ge=1,
        description="DNS query timeout in seconds.",
    )
    max_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum subdomain enumeration depth.",
    )
    recursive: bool = Field(
        default=True,
        description="Enable recursive subdomain enumeration.",
    )


class HTTPConfig(BaseConfig):
    """Built-in HTTP probing configuration."""

    model_config = SettingsConfigDict(env_prefix="OSINTOTE_HTTP_")

    timeout: int = Field(
        default=10,
        ge=1,
        le=120,
        description="Per-request timeout in seconds.",
    )
    concurrency: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum concurrent HTTP probes.",
    )
    user_agent: str = Field(
        default="Mozilla/5.0 (compatible; OSINTote/0.0.1)",
        description="User-Agent string for HTTP requests.",
    )
    follow_redirects: bool = Field(
        default=True,
        description="Follow HTTP redirects (up to 10).",
    )
    status_codes: list[int] = Field(
        default=[200, 301, 302, 403, 404, 500],
        description="HTTP status codes to include in results.",
    )


# ── AI / LLM ─────────────────────────────────────────────────────────


class AIClientConfig(BaseSettings):
    """AI / LLM provider configuration.

    Supports any OpenAI-compatible HTTP API (Ollama, LM Studio, llama.cpp,
    vLLM, OpenAI, etc.).  Settings are read from
    ``OSINTOTE_AI_*`` environment variables.
    """

    model_config = SettingsConfigDict(env_prefix="OSINTOTE_AI_")

    enabled: bool = Field(
        default=False,
        description="Enable AI-powered analysis.",
    )
    provider: Literal["openai", "ollama", "lmstudio", "llamacpp", "vllm", "custom"] = Field(
        default="custom",
        description="AI provider type.",
    )
    base_url: str = Field(
        default="http://localhost:11434/v1",
        description="Base URL for the AI API (OpenAI-compatible).",
    )
    api_key: SecretStr | None = Field(
        default=None,
        description="API key (required for some providers, can be dummy for Ollama).",
    )
    model: str = Field(
        default="llama3",
        description="Model identifier (e.g. llama3, mistral, gpt-3.5-turbo).",
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=128000,
        description="Maximum tokens per request.",
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (lower = more deterministic).",
    )
    context_window: int = Field(
        default=5000,
        ge=500,
        description="Maximum context window size in tokens for analysis.",
    )
    timeout: int = Field(
        default=120,
        ge=5,
        description="Request timeout in seconds.",
    )


# ── aggregated config ────────────────────────────────────────────────


class EngineConfig(BaseSettings):
    """Top-level engine configuration aggregator.

    Reads every per-source config from its own environment variable
    namespace, and exposes them as typed attributes::

        cfg = EngineConfig.load()
        print(cfg.shodan.rate_limit)    # → 1
        print(cfg.http.concurrency)     # → 50
    """

    # intelligence API sources
    shodan: ShodanConfig = Field(default_factory=ShodanConfig)
    censys: CensysConfig = Field(default_factory=CensysConfig)
    virustotal: VirusTotalConfig = Field(default_factory=VirusTotalConfig)

    # CLI / tool wrappers
    nmap: NmapConfig = Field(default_factory=NmapConfig)
    subfinder: SubfinderConfig = Field(default_factory=SubfinderConfig)
    nuclei: NucleiConfig = Field(default_factory=NucleiConfig)
    whois: WhoisConfig = Field(default_factory=WhoisConfig)

    # built-in stages
    dns: DNSConfig = Field(default_factory=DNSConfig)
    http: HTTPConfig = Field(default_factory=HTTPConfig)

    # AI
    ai: AIClientConfig = Field(default_factory=AIClientConfig)

    # general
    db_path: str = Field(
        default="./osintote.db",
        description="Path to the SQLite database file.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging verbosity.",
    )
    log_dir: str = Field(
        default="./.osintote/logs",
        description="Directory for log file rotation.",
    )
    log_max_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10 MB
        ge=1024,
        description="Max size per log file before rotation.",
    )
    log_backup_count: int = Field(
        default=5,
        ge=0,
        description="Number of rotated log files to keep.",
    )

    # concurrency
    max_concurrent_tasks: int = Field(
        default=4,
        ge=1,
        le=64,
        description="Maximum concurrent in-flight tasks.",
    )
    io_workers: int = Field(
        default=8,
        ge=1,
        le=128,
        description="Number of async I/O workers (event-loop threads).",
    )
    cpu_workers: int = Field(
        default=2,
        ge=1,
        le=32,
        description="Number of CPU-bound workers (process pool).",
    )
    task_timeout: int = Field(
        default=3600,  # 1 hour
        ge=60,
        description="Global task timeout in seconds (soft limit).",
    )

    model_config = SettingsConfigDict(env_prefix="OSINTOTE_")

    # ── public helpers ───────────────────────────────────────────

    @classmethod
    def load(cls, overrides: dict | None = None) -> EngineConfig:
        """Load configuration from environment + optional dict overrides.

        ``overrides`` is a flat dict whose keys mirror the dotted config
        path (e.g. ``{"shodan.api_key": "sk-..."}``).  Overrides take
        precedence over environment variables.
        """
        from pydantic_settings import SettingsConfigDict

        # Build a nested dict from flat overrides
        nested: dict = {}
        for key, value in (overrides or {}).items():
            parts = key.split(".")
            d = nested
            for part in parts[:-1]:
                d = d.setdefault(part, {})
            d[parts[-1]] = value

        # Merge with environment using nested delimiter
        _env_overrides = SettingsConfigDict(env_prefix="OSINTOTE_", env_nested_delimiter="__")
        return cls(**nested)

    def as_dict(self, *, secrets: bool = False) -> dict:
        """Return a serialisable representation of the config.

        When ``secrets=False`` (default), any ``SecretStr`` fields are
        masked as ``"****"`` so the result is safe to log.
        """
        import json

        data = self.model_dump(mode="python")

        def _mask(obj: object) -> object:
            if isinstance(obj, SecretStr):
                return "****" if not secrets else obj.get_secret_value()
            if isinstance(obj, dict):
                return {k: _mask(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_mask(item) for item in obj]
            return obj

        return json.loads(json.dumps(_mask(data)))

    def summary(self) -> str:
        """Return a human-readable config summary for CLI / logs."""
        lines: list[str] = []
        lines.append("OSINTote Engine Configuration")
        lines.append("=" * 40)
        lines.append(f"  DB path:          {self.db_path}")
        lines.append(f"  Log level:        {self.log_level}")
        lines.append(f"  Log dir:          {self.log_dir}")
        lines.append(f"  Max concurrent:   {self.max_concurrent_tasks}")
        lines.append(f"  I/O workers:      {self.io_workers}")
        lines.append(f"  CPU workers:      {self.cpu_workers}")
        lines.append(f"  Task timeout:     {self.task_timeout}s")
        lines.append("")

        # sources
        sources = [
            ("Shodan", self.shodan),
            ("Censys", self.censys),
            ("VirusTotal", self.virustotal),
            ("Nmap", self.nmap),
            ("Subfinder", self.subfinder),
            ("Nuclei", self.nuclei),
            ("Whois", self.whois),
            ("DNS", self.dns),
            ("HTTP", self.http),
            ("AI", self.ai),
        ]
        for name, cfg in sources:
            enabled = "✓" if cfg.enabled else "✗"
            lines.append(f"  [{enabled}] {name}")
            if isinstance(cfg, (ShodanConfig, CensysConfig, VirusTotalConfig, AIClientConfig)):
                has_key = bool(cfg.api_key or getattr(cfg, "api_secret", None))
                lines.append(f"        API key:      {'configured' if has_key else 'missing'}")
            if hasattr(cfg, "rate_limit"):
                lines.append(f"        Rate limit:   {cfg.rate_limit}")
            if hasattr(cfg, "binary_path"):
                lines.append(f"        Binary:       {cfg.binary_path}")

        return "\n".join(lines)
