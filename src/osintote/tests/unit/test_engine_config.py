"""Unit tests for engine configuration (Pydantic BaseSettings)."""

from __future__ import annotations

import os
import json
from pathlib import Path

import pytest
from pydantic import SecretStr

from osintote.engine.config import (
    EngineConfig,
    ShodanConfig,
    CensysConfig,
    VirusTotalConfig,
    NmapConfig,
    SubfinderConfig,
    NucleiConfig,
    WhoisConfig,
    DNSConfig,
    HTTPConfig,
    AIClientConfig,
)


# ── default values ──────────────────────────────────────────────────


class TestDefaultValues:
    """Verify every config field has the correct default."""

    def test_engine_defaults(self) -> None:
        cfg = EngineConfig()
        assert cfg.db_path == "./osintote.db"
        assert cfg.log_level == "INFO"
        assert cfg.max_concurrent_tasks == 4
        assert cfg.io_workers == 8
        assert cfg.cpu_workers == 2
        assert cfg.task_timeout == 3600
        assert cfg.ai.enabled is False
        assert cfg.shodan.enabled is True
        assert cfg.http.enabled is True

    def test_shodan_defaults(self) -> None:
        cfg = ShodanConfig()
        assert cfg.enabled is True
        assert cfg.api_key is None
        assert cfg.rate_limit == 1
        assert cfg.cooldown_minutes == 5

    def test_censys_defaults(self) -> None:
        cfg = CensysConfig()
        assert cfg.enabled is True
        assert cfg.api_key is None
        assert cfg.api_secret is None
        assert cfg.rate_limit == 5

    def test_virustotal_defaults(self) -> None:
        cfg = VirusTotalConfig()
        assert cfg.enabled is True
        assert cfg.api_key is None
        assert cfg.rate_limit == 4

    def test_nmap_defaults(self) -> None:
        cfg = NmapConfig()
        assert cfg.binary_path == "nmap"
        assert cfg.timeout == 300
        assert cfg.scan_type == "-Pn"
        assert cfg.service_detection is True
        assert cfg.timing == "T3"
        assert cfg.max_hosts == 1000

    def test_subfinder_defaults(self) -> None:
        cfg = SubfinderConfig()
        assert cfg.binary_path == "subfinder"
        assert cfg.rate_limit == 0

    def test_nuclei_defaults(self) -> None:
        cfg = NucleiConfig()
        assert cfg.binary_path == "nuclei"
        assert cfg.timeout == 120
        assert cfg.severity == ["info", "low", "medium", "high", "critical"]
        assert cfg.rate_limit == 0
        assert cfg.templates == ""

    def test_whois_defaults(self) -> None:
        cfg = WhoisConfig()
        assert cfg.enabled is True
        assert cfg.timeout == 10

    def test_dns_defaults(self) -> None:
        cfg = DNSConfig()
        assert cfg.enabled is True
        assert cfg.resolver_timeout == 5
        assert cfg.max_depth == 3
        assert cfg.recursive is True

    def test_http_defaults(self) -> None:
        cfg = HTTPConfig()
        assert cfg.enabled is True
        assert cfg.timeout == 10
        assert cfg.concurrency == 50
        assert cfg.user_agent == "Mozilla/5.0 (compatible; OSINTote/0.0.1)"
        assert cfg.follow_redirects is True
        assert cfg.status_codes == [200, 301, 302, 403, 404, 500]

    def test_ai_defaults(self) -> None:
        cfg = AIClientConfig()
        assert cfg.enabled is False
        assert cfg.provider == "custom"
        assert cfg.base_url == "http://localhost:11434/v1"
        assert cfg.model == "llama3"
        assert cfg.max_tokens == 4096
        assert cfg.temperature == 0.3
        assert cfg.context_window == 5000
        assert cfg.timeout == 120


# ── environment variable loading ────────────────────────────────────


class TestEnvVars:
    """Verify os.environ → Pydantic BaseSettings resolution."""

    def test_env_prefix_osintote_shodan(self) -> None:
        env = {"OSINTOTE_SHODAN_API_KEY": "test-shodan-key-123"}
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("OSINTOTE_SHODAN_API_KEY", "test-shodan-key-123")
            cfg = ShodanConfig()
            assert cfg.api_key is not None
            assert cfg.api_key.get_secret_value() == "test-shodan-key-123"

    def test_env_prefix_osintote_censys(self) -> None:
        env = {
            "OSINTOTE_CENSYS_API_KEY": "censys-user",
            "OSINTOTE_CENSYS_API_SECRET": "censys-secret",
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("OSINTOTE_CENSYS_API_KEY", "censys-user")
            mp.setenv("OSINTOTE_CENSYS_API_SECRET", "censys-secret")
            cfg = CensysConfig()
            assert cfg.api_key is not None
            assert cfg.api_key.get_secret_value() == "censys-user"
            assert cfg.api_secret is not None
            assert cfg.api_secret.get_secret_value() == "censys-secret"

    def test_env_prefix_osintote_virustotal(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("OSINTOTE_VT_API_KEY", "vt-key-xyz")
            cfg = VirusTotalConfig()
            assert cfg.api_key is not None
            assert cfg.api_key.get_secret_value() == "vt-key-xyz"

    def test_env_prefix_osintote_ai(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("OSINTOTE_AI_BASE_URL", "http://localhost:8080/v1")
            mp.setenv("OSINTOTE_AI_MODEL", "mistral")
            mp.setenv("OSINTOTE_AI_ENABLED", "true")
            cfg = AIClientConfig()
            assert cfg.base_url == "http://localhost:8080/v1"
            assert cfg.model == "mistral"
            assert cfg.enabled is True

    def test_env_prefix_osintote_http(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("OSINTOTE_HTTP_TIMEOUT", "30")
            mp.setenv("OSINTOTE_HTTP_CONCURRENCY", "200")
            cfg = HTTPConfig()
            assert cfg.timeout == 30
            assert cfg.concurrency == 200

    def test_env_prefix_osintote_engine(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("OSINTOTE_DB_PATH", "/tmp/test.db")
            mp.setenv("OSINTOTE_LOG_LEVEL", "DEBUG")
            mp.setenv("OSINTOTE_MAX_CONCURRENT_TASKS", "8")
            cfg = EngineConfig()
            assert cfg.db_path == "/tmp/test.db"
            assert cfg.log_level == "DEBUG"
            assert cfg.max_concurrent_tasks == 8


# ── overrides ────────────────────────────────────────────────────────


class TestOverrides:
    """Verify dict overrides take precedence over env vars."""

    def test_overrides_shodan(self) -> None:
        cfg = EngineConfig.load(overrides={"shodan.api_key": "override-key"})
        assert cfg.shodan.api_key.get_secret_value() == "override-key"

    def test_overrides_http(self) -> None:
        cfg = EngineConfig.load(overrides={"http.concurrency": 1})
        assert cfg.http.concurrency == 1

    def test_overrides_db_path(self) -> None:
        cfg = EngineConfig.load(overrides={"db_path": "/custom/path.db"})
        assert cfg.db_path == "/custom/path.db"


# ── validation ───────────────────────────────────────────────────────


class TestValidation:
    """Verify field validators reject bad input."""

    def test_empty_api_key_raises(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("OSINTOTE_SHODAN_API_KEY", "  ")
            with pytest.raises(ValueError, match="must not be empty"):
                ShodanConfig()

    def test_empty_censys_key_raises(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("OSINTOTE_CENSYS_API_KEY", "  ")
            with pytest.raises(ValueError, match="must not be empty"):
                CensysConfig()

    def test_empty_censys_secret_raises(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("OSINTOTE_CENSYS_API_SECRET", "  ")
            with pytest.raises(ValueError, match="must not be empty"):
                CensysConfig()

    def test_empty_vt_key_raises(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("OSINTOTE_VT_API_KEY", "  ")
            with pytest.raises(ValueError, match="must not be empty"):
                VirusTotalConfig()

    def test_rate_limit_bounds(self) -> None:
        with pytest.raises(ValueError):
            ShodanConfig(rate_limit=0)
        with pytest.raises(ValueError):
            ShodanConfig(rate_limit=101)

    def test_http_concurrency_bounds(self) -> None:
        with pytest.raises(ValueError):
            HTTPConfig(concurrency=0)
        with pytest.raises(ValueError):
            HTTPConfig(concurrency=501)


# ── serialisation ────────────────────────────────────────────────────


class TestSerialisation:
    """Verify as_dict() and summary()."""

    def test_as_dict_no_secrets(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("OSINTOTE_SHODAN_API_KEY", "sk-test")
            mp.setenv("OSINTOTE_VT_API_KEY", "vt-test")
            cfg = EngineConfig()
            data = cfg.as_dict(secrets=False)
            assert data["shodan"]["api_key"] == "****"
            assert data["virustotal"]["api_key"] == "****"

    def test_as_dict_with_secrets(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("OSINTOTE_SHODAN_API_KEY", "sk-test")
            cfg = EngineConfig()
            data = cfg.as_dict(secrets=True)
            assert data["shodan"]["api_key"] == "sk-test"

    def test_as_dict_is_json(self) -> None:
        cfg = EngineConfig()
        data = cfg.as_dict()
        raw = json.dumps(data)  # must not raise
        assert "osintote" in raw.lower() or "shodan" in raw

    def test_summary_contains_keys(self) -> None:
        cfg = EngineConfig.load(overrides={"shodan.api_key": "x"})
        text = cfg.summary()
        assert "OSINTote Engine Configuration" in text
        assert "Shodan" in text
        assert "HTTP" in text
        assert "API key" in text
        assert "Rate limit" in text


# ── repr ─────────────────────────────────────────────────────────────


class TestRepr:
    def test_base_config_repr(self) -> None:
        cfg = ShodanConfig()
        assert repr(cfg) == "ShodanConfig()"
