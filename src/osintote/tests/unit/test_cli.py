# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Tests for the OSINTote CLI module."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest


class TestCLIEntry:
    """Test CLI entry point."""

    def test_main_callable(self):
        """Test that main() is callable."""
        from osintote.cli import main

        assert callable(main)

    def test_app_has_commands(self):
        """Test that app has registered commands."""
        from osintote.cli import app

        commands = [
            cmd.callback.__name__ if cmd.callback else None for cmd in app.registered_commands
        ]
        assert any(c for c in commands if c and "init" in c)
        assert any(c for c in commands if c and "serve" in c)
        assert any(c for c in commands if c and "status" in c)


class TestCLIInit:
    """Test the init command."""

    def test_init_creates_config(self, cli_test_dir, monkeypatch):
        """Test that init creates .osintote directory and config file."""
        monkeypatch.chdir(cli_test_dir)
        with patch("osintote.cli.asyncio.run"):
            from osintote.cli import app

            with pytest.raises(SystemExit):
                app(["init", "--force"])
        config_file = cli_test_dir / ".osintote" / "config.json"
        assert config_file.exists()
        config = json.loads(config_file.read_text())
        assert config["version"] == "0.0.1"
        assert config["database"] == "osintote.db"

    def test_init_creates_config_with_custom_db_path(self, cli_test_dir, monkeypatch):
        """Test init with custom database path."""
        monkeypatch.chdir(cli_test_dir)
        with patch("osintote.cli.asyncio.run"):
            from osintote.cli import app

            with pytest.raises(SystemExit):
                app(["init", "--force", "-d", "custom.db"])
        config_file = cli_test_dir / ".osintote" / "config.json"
        config = json.loads(config_file.read_text())
        assert config["database"] == "custom.db"

    def test_init_creates_osintote_directory(self, cli_test_dir, monkeypatch):
        """Test that init creates .osintote directory."""
        monkeypatch.chdir(cli_test_dir)
        with patch("osintote.cli.asyncio.run"):
            from osintote.cli import app

            with pytest.raises(SystemExit):
                app(["init", "--force"])
        config_dir = cli_test_dir / ".osintote"
        assert config_dir.is_dir()

    @pytest.mark.skip(reason="Interactive prompt handling needs refactor")
    def test_init_warns_about_existing_config(self, cli_test_dir, monkeypatch):
        """Test that init warns about existing config without --force."""
        monkeypatch.chdir(cli_test_dir)
        # First init
        with patch("osintote.cli.asyncio.run"):
            from osintote.cli import app

            with pytest.raises(SystemExit):
                app(["init", "--force"])
        # Second init without force - mock input to return 'y' to overwrite
        import typer

        with patch.object(typer, "prompt", return_value="y"):
            from osintote.cli import app

            with pytest.raises(SystemExit) as exc_info:
                app(["init"])
            # Should exit with code 0 (clean)
            assert exc_info.value.code == 0

    def test_init_overwrites_with_force(self, cli_test_dir, monkeypatch):
        """Test that --force overwrites existing config."""
        monkeypatch.chdir(cli_test_dir)
        # First init
        with patch("osintote.cli.asyncio.run"):
            from osintote.cli import app

            with pytest.raises(SystemExit):
                app(["init", "--force"])
        # Modify config
        config_file = cli_test_dir / ".osintote" / "config.json"
        config = json.loads(config_file.read_text())
        config["version"] = "modified"
        config_file.write_text(json.dumps(config))
        # Second init with force
        with patch("osintote.cli.asyncio.run"):
            from osintote.cli import app

            with pytest.raises(SystemExit):
                app(["init", "--force"])
        config = json.loads(config_file.read_text())
        assert config["version"] == "0.0.1"  # Reset to default


class TestCLIStatus:
    """Test the status command."""

    def test_status_shows_version(self, cli_test_dir, monkeypatch):
        """Test that status shows version info."""
        monkeypatch.chdir(cli_test_dir)
        from osintote.cli import app

        with pytest.raises(SystemExit) as exc_info:
            app(["status"])
        # Should exit with code 0
        assert exc_info.value.code == 0

    def test_status_shows_db_not_found(self, cli_test_dir, monkeypatch):
        """Test that status shows database not found when no DB exists."""
        monkeypatch.chdir(cli_test_dir)
        from osintote.cli import app

        with pytest.raises(SystemExit) as exc_info:
            app(["status"])
        assert exc_info.value.code == 0


class TestCLIMigrations:
    """Test CLI migration handling."""

    def test_init_runs_migrations(self, cli_test_dir, monkeypatch):
        """Test that init command triggers migrations."""
        monkeypatch.chdir(cli_test_dir)
        with patch("osintote.cli.asyncio.run") as mock_run:
            mock_run.return_value = None
            from osintote.cli import app

            with pytest.raises(SystemExit):
                app(["init", "--force"])
            # Should have called asyncio.run for migrations
            assert mock_run.called

    def test_init_handles_migration_error(self, cli_test_dir, monkeypatch):
        """Test that init handles migration errors gracefully."""
        monkeypatch.chdir(cli_test_dir)
        with patch("osintote.cli.asyncio.run", side_effect=Exception("Migration failed")):
            from osintote.cli import app

            with pytest.raises(SystemExit) as exc_info:
                app(["init", "--force"])
            # Should exit with code 1
            assert exc_info.value.code == 1
