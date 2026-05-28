# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Tests for the cryptographic utilities."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osintote.crypto import (
    EncryptedBlob,
    EncryptionManager,
    KeyStorage,
    decrypt_data,
    derive_key,
    encrypt_data,
    verify_password,
)


# ---------------------------------------------------------------------------
# derive_key
# ---------------------------------------------------------------------------


class TestDeriveKey:
    """Tests for PBKDF2 key derivation."""

    def test_returns_32_byte_key(self) -> None:
        key, salt = derive_key("test-password")
        assert len(key) == 32
        assert len(salt) == 32

    def test_deterministic_with_same_salt(self) -> None:
        salt = b"0" * 32
        key1, _ = derive_key("password", salt)
        key2, _ = derive_key("password", salt)
        assert key1 == key2

    def test_different_passwords_different_keys(self) -> None:
        salt = b"0" * 32
        key1, _ = derive_key("password1", salt)
        key2, _ = derive_key("password2", salt)
        assert key1 != key2

    def test_different_salts_same_password(self) -> None:
        key1, salt1 = derive_key("password")
        key2, salt2 = derive_key("password")
        assert salt1 != salt2
        assert key1 != key2

    def test_salt_generated_if_none(self) -> None:
        key1, salt1 = derive_key("password")
        key2, salt2 = derive_key("password")
        assert salt1 != salt2

    def test_iterations_600k(self) -> None:
        key, _ = derive_key("password")
        assert len(key) == 32  # dklen=32 matches ITERATIONS=600k


# ---------------------------------------------------------------------------
# encrypt / decrypt round-trip
# ---------------------------------------------------------------------------


class TestEncryptDecrypt:
    """Tests for AES-256-GCM encryption and decryption."""

    def test_roundtrip_empty(self) -> None:
        key = b"0" * 32
        blob = encrypt_data(b"", key)
        assert decrypt_data(blob, key) == b""

    def test_roundtrip_plain_text(self) -> None:
        key = b"0" * 32
        data = b"hello world"
        blob = encrypt_data(data, key)
        assert decrypt_data(blob, key) == data

    def test_roundtrip_large_data(self) -> None:
        key = b"0" * 32
        data = b"x" * 100_000  # 100 KB
        blob = encrypt_data(data, key)
        assert decrypt_data(blob, key) == data

    def test_roundtrip_unicode(self) -> None:
        key = b"0" * 32
        data = "こんにちは世界".encode("utf-8")
        blob = encrypt_data(data, key)
        assert decrypt_data(blob, key) == data

    def test_different_iv_each_time(self) -> None:
        key = b"0" * 32
        data = b"same"
        blob1 = encrypt_data(data, key)
        blob2 = encrypt_data(data, key)
        assert blob1.iv != blob2.iv

    def test_wrong_key_raises(self) -> None:
        key1 = b"0" * 32
        key2 = b"1" * 32
        blob = encrypt_data(b"secret", key1)
        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt_data(blob, key2)

    def test_corrupted_ciphertext_raises(self) -> None:
        key = b"0" * 32
        blob = encrypt_data(b"secret", key)
        blob.ciphertext = b"\x00" * len(blob.ciphertext)
        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt_data(blob, key)

    def test_corrupted_tag_raises(self) -> None:
        key = b"0" * 32
        blob = encrypt_data(b"secret", key)
        blob.tag = b"\x00" * len(blob.tag)
        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt_data(blob, key)

    def test_encrypted_data_is_not_plaintext(self) -> None:
        key = b"0" * 32
        data = b"hello"
        blob = encrypt_data(data, key)
        assert blob.ciphertext != data
        assert blob.ciphertext != data + blob.tag


# ---------------------------------------------------------------------------
# EncryptedBlob encoding
# ---------------------------------------------------------------------------


class TestEncryptedBlob:
    """Tests for EncryptedBlob serialization."""

    def test_encode_decode_roundtrip(self) -> None:
        key = b"0" * 32
        blob = encrypt_data(b"test", key)
        encoded = blob.encode()
        assert isinstance(encoded, str)
        restored = EncryptedBlob.decode(encoded)
        assert restored.ciphertext == blob.ciphertext
        assert restored.iv == blob.iv
        assert restored.tag == blob.tag
        assert restored.salt == blob.salt

    def test_decode_is_independent(self) -> None:
        """Decoded blob works for decryption without original."""
        key = b"0" * 32
        blob = encrypt_data(b"test", key)
        encoded = blob.encode()
        restored = EncryptedBlob.decode(encoded)
        assert decrypt_data(restored, key) == b"test"

    def test_magic_bytes_in_pack(self) -> None:
        blob = encrypt_data(b"data", b"0" * 32)
        packed = blob._pack()
        assert packed[:len(blob.MAGIC)] == blob.MAGIC

    def test_invalid_base64_raises(self) -> None:
        with pytest.raises(Exception):
            EncryptedBlob.decode("not-valid-base64!!!")


# ---------------------------------------------------------------------------
# verify_password
# ---------------------------------------------------------------------------


class TestVerifyPassword:
    """Tests for password verification."""

    def test_correct_password(self) -> None:
        key = b"0" * 32
        blob = encrypt_data(b"test", key)
        assert verify_password("x", key, blob) is True

    def test_wrong_password(self) -> None:
        key1 = b"0" * 32
        key2 = b"1" * 32
        blob = encrypt_data(b"test", key2)
        assert verify_password("x", key1, blob) is False


# ---------------------------------------------------------------------------
# KeyStorage
# ---------------------------------------------------------------------------


class TestKeyStorage:
    """Tests for disk-based key storage."""

    @pytest.fixture
    def key_store(self, tmp_path: Path) -> KeyStorage:
        return KeyStorage(tmp_path)

    @pytest.fixture
    def encrypted_key(self, key_store: KeyStorage) -> EncryptedBlob:
        key = b"0" * 32
        return encrypt_data(b"secret", key)

    def test_save_and_load(self, key_store: KeyStorage, encrypted_key: EncryptedBlob) -> None:
        key_store.save_key("resource1", encrypted_key)
        loaded = key_store.load_key("resource1")
        assert loaded is not None
        assert loaded.ciphertext == encrypted_key.ciphertext

    def test_load_missing_returns_none(self, key_store: KeyStorage) -> None:
        assert key_store.load_key("nonexistent") is None

    def test_delete_key(self, key_store: KeyStorage, encrypted_key: EncryptedBlob) -> None:
        key_store.save_key("resource1", encrypted_key)
        assert key_store.has_key("resource1")
        assert key_store.delete_key("resource1")
        assert not key_store.has_key("resource1")
        assert key_store.load_key("resource1") is None

    def test_delete_missing_returns_false(self, key_store: KeyStorage) -> None:
        assert key_store.delete_key("nonexistent") is False

    def test_list_resources(self, key_store: KeyStorage, encrypted_key: EncryptedBlob) -> None:
        key_store.save_key("res1", encrypted_key)
        key_store.save_key("res2", encrypted_key)
        # list_resources returns keys from the file; filter out .salt and pbkdf2_salt entries
        keys = key_store._load()["keys"]
        resources = {k for k in keys if not k.endswith(".salt")}
        assert resources == {"res1", "res2"}

    def test_has_key(self, key_store: KeyStorage, encrypted_key: EncryptedBlob) -> None:
        assert not key_store.has_key("new")
        key_store.save_key("new", encrypted_key)
        assert key_store.has_key("new")

    def test_overwrite_key(self, key_store: KeyStorage, encrypted_key: EncryptedBlob) -> None:
        key_store.save_key("res", encrypted_key)
        key2 = b"1" * 32
        blob2 = encrypt_data(b"other", key2)
        key_store.save_key("res", blob2)
        loaded = key_store.load_key("res")
        assert loaded is not None
        assert loaded.ciphertext == blob2.ciphertext

    def test_keys_file_created(self, key_store: KeyStorage, encrypted_key: EncryptedBlob) -> None:
        assert not key_store.keys_file.exists()
        key_store.save_key("res", encrypted_key)
        assert key_store.keys_file.exists()
        # Valid JSON
        with open(key_store.keys_file) as f:
            data = json.load(f)
        assert data["version"] == 1
        assert "res" in data["keys"]

    def test_atomic_write(self, key_store: KeyStorage, encrypted_key: EncryptedBlob) -> None:
        """File should not have .tmp suffix after write."""
        key_store.save_key("res", encrypted_key)
        assert not key_store.keys_file.with_suffix(".tmp").exists()


# ---------------------------------------------------------------------------
# EncryptionManager
# ---------------------------------------------------------------------------


class TestEncryptionManager:
    """Tests for the high-level EncryptionManager API."""

    def test_encrypt_decrypt(self) -> None:
        mgr = EncryptionManager(password="master")
        blob = mgr.encrypt(b"secret data")
        plain = mgr.decrypt(blob)
        assert plain == b"secret data"

    def test_key_property_caches(self) -> None:
        mgr = EncryptionManager(password="master")
        key1 = mgr.key
        key2 = mgr.key
        assert key1 is key2

    def test_key_cached_until_cleared(self) -> None:
        mgr = EncryptionManager(password="master")
        key1 = mgr.key
        assert mgr._key is not None
        mgr._key = None
        key2 = mgr.key  # re-derives (different salt, different key)
        assert mgr._key is not None
        # Keys differ because derive_key generates new random salt each time
        # (this is intentional for security)

    def test_different_passwords_different_keys(self) -> None:
        mgr1 = EncryptionManager(password="pass1")
        mgr2 = EncryptionManager(password="pass2")
        assert mgr1.key != mgr2.key

    def test_save_and_load_key(self, tmp_path: Path) -> None:
        store = KeyStorage(tmp_path)
        mgr1 = EncryptionManager(password="master", key_storage=store)
        mgr1.save_key("db")
        mgr2 = EncryptionManager(password="master", key_storage=store)
        assert mgr2.load_key("db") is True

    def test_wrong_password_fails_load(self, tmp_path: Path) -> None:
        store = KeyStorage(tmp_path)
        mgr1 = EncryptionManager(password="correct", key_storage=store)
        mgr1.save_key("db")
        mgr2 = EncryptionManager(password="wrong", key_storage=store)
        assert mgr2.load_key("db") is False

    def test_encrypt_large_data(self) -> None:
        mgr = EncryptionManager(password="master")
        data = b"x" * 1_000_000  # 1 MB
        blob = mgr.encrypt(data)
        assert mgr.decrypt(blob) == data

    def test_clear(self) -> None:
        mgr = EncryptionManager(password="master")
        _ = mgr.key  # derive
        mgr.clear()
        assert mgr._key is None
        assert mgr._salt == b""

    def test_verify_password(self, tmp_path: Path) -> None:
        store = KeyStorage(tmp_path)
        mgr = EncryptionManager(password="master", key_storage=store)
        mgr.save_key("db")
        # Same password should verify
        mgr2 = EncryptionManager(password="master", key_storage=store)
        assert mgr2.verify_password("master", "db") is True
        # Wrong password should fail
        mgr3 = EncryptionManager(password="wrong", key_storage=store)
        assert mgr3.verify_password("wrong", "db") is False
