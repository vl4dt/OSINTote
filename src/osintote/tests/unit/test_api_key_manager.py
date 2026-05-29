# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for the API Key Manager."""

import uuid

from sqlmodel import Session

from osintote.api.manager import ApiKeyManager


class TestApiKeyManager:
    """Tests for ApiKeyManager CRUD and key resolution."""

    def test_add_key(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        key = manager.add("Test Key", "shodan", "sk-test-123")

        assert key.name == "Test Key"
        assert key.source == "shodan"
        assert key.key == "sk-test-123"
        assert key.primary is False
        assert key.fallback is False
        assert key.id is not None

    def test_add_primary_key(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        # Add a primary key first
        manager.add("Primary Key", "openai", "sk-old", primary=True)
        # Add another primary — should deactivate the first
        new_key = manager.add("New Primary", "openai", "sk-new", primary=True)

        existing = manager.get(new_key.id)
        assert existing is not None

        all_keys = manager.list_by_source("openai")
        primaries = [k for k in all_keys if k.primary]
        assert len(primaries) == 1
        assert primaries[0].name == "New Primary"

    def test_get_key(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        key = manager.add("Test", "shodan", "sk-test")
        fetched = manager.get(key.id)

        assert fetched is not None
        assert fetched.id == key.id

    def test_get_key_not_found(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        fake_id = uuid.uuid4()
        result = manager.get(fake_id)
        assert result is None

    def test_list_by_source(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        manager.add("Key1", "shodan", "sk-1")
        manager.add("Key2", "shodan", "sk-2")
        manager.add("Key3", "virustotal", "sk-3")

        shodan_keys = manager.list_by_source("shodan")
        vt_keys = manager.list_by_source("virustotal")

        assert len(shodan_keys) == 2
        assert len(vt_keys) == 1
        assert vt_keys[0].source == "virustotal"

    def test_list_all(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        manager.add("Key1", "shodan", "sk-1")
        manager.add("Key2", "openai", "sk-2")

        all_keys = manager.list_all()
        assert len(all_keys) == 2

    def test_get_primary(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        primary = manager.add("Primary", "shodan", "sk-primary", primary=True)
        fallback = manager.add("Fallback", "shodan", "sk-fallback", fallback=True)

        assert manager.get_primary("shodan").id == primary.id
        assert manager.get_fallback("shodan").id == fallback.id
        assert manager.get_primary("openai") is None

    def test_rotate_primary(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        old_primary = manager.add("Old Primary", "openai", "sk-old", primary=True)

        rotated = manager.rotate_primary("openai", "sk-new", "New Primary")

        assert rotated.primary is True
        assert rotated.name == "New Primary"
        assert old_primary.id != rotated.id

        all_keys = manager.list_by_source("openai")
        primaries = [k for k in all_keys if k.primary]
        assert len(primaries) == 1
        assert primaries[0].id == rotated.id

    def test_update_key(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        key = manager.add("Test", "shodan", "sk-old")

        updated = manager.update(key, name="Updated Key", fallback=True)
        assert updated.name == "Updated Key"
        assert updated.fallback is True

    def test_update_sets_primary_deactivates_others(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        k1 = manager.add("K1", "shodan", "sk-1", primary=True)
        k2 = manager.add("K2", "shodan", "sk-2")

        updated = manager.update(k2, primary=True)
        assert updated.primary is True

        k1_ref = manager.get(k1.id)
        assert k1_ref is not None
        assert k1_ref.primary is False

    def test_delete_key(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        key = manager.add("Test", "shodan", "sk-test")
        manager.delete(key)

        assert manager.get(key.id) is None

    def test_get_all_keys_for_source(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        manager.add("Primary", "shodan", "sk-primary", primary=True)
        manager.add("Fallback", "shodan", "sk-fallback", fallback=True)

        keys = manager.get_all_keys_for_source("shodan")
        assert keys["primary"] == "sk-primary"
        assert keys["fallback"] == "sk-fallback"

    def test_get_all_keys_for_source_missing(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        keys = manager.get_all_keys_for_source("nonexistent")
        assert keys == {"primary": None, "fallback": None}

    def test_resolve_key_primary_fallback(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        manager.add("Primary", "shodan", "sk-primary", primary=True)
        manager.add("Fallback", "shodan", "sk-fallback", fallback=True)

        resolved = manager.resolve_key("shodan")
        assert resolved == "sk-primary"

    def test_resolve_key_only_fallback(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        manager.add("Fallback", "shodan", "sk-fallback", fallback=True)

        resolved = manager.resolve_key("shodan")
        assert resolved == "sk-fallback"

    def test_resolve_key_no_keys(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        resolved = manager.resolve_key("nonexistent")
        assert resolved is None

    def test_add_with_target_id(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        target_id = uuid.uuid4()
        key = manager.add("Test", "shodan", "sk-test", target_id=target_id)

        assert key.target_id == target_id

    def test_rotate_with_custom_name(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        rotated = manager.rotate_primary(
            "shodan", "sk-new", new_name="Custom New Key"
        )
        assert rotated.name == "Custom New Key"
        assert rotated.primary is True

    def test_list_by_source_empty(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        result = manager.list_by_source("nonexistent")
        assert result == []

    def test_list_by_source_ordered(self, session: Session) -> None:
        manager = ApiKeyManager(session)
        k1 = manager.add("First", "shodan", "sk-1")
        k2 = manager.add("Second", "shodan", "sk-2")

        keys = manager.list_by_source("shodan")
        assert keys[0].id == k1.id
        assert keys[1].id == k2.id
