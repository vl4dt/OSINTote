# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Cryptographic utilities for OSINTote.

Provides AES-256-GCM encryption with PBKDF2-HMAC-SHA256 master password
derivation, plus helpers to securely store and retrieve encryption keys
from the configuration directory.

Usage::

    from osintote.crypto import EncryptionManager, KeyStorage

    mgr = EncryptionManager(password="master-secret")
    ciphertext = mgr.encrypt(b"secret data")
    plaintext = mgr.decrypt(ciphertext)  # bytes
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# PBKDF2 parameters
SALT_SIZE = 32           # 256-bit salt
ITERATIONS = 600_000     # OWASP 2023 recommendation for PBKDF2-HMAC-SHA256
KEY_SIZE = 32            # 256-bit key (AES-256)
TAG_SIZE = 16            # 128-bit GCM auth tag
IV_SIZE = 12             # 96-bit GCM nonce
MAGIC = b"OSINTOTE-AES256GCM"  # magic bytes for file format detection


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class EncryptedBlob:
    """Container for an encrypted payload.

    Attributes
    ----------
    ciphertext : bytes
        The encrypted data.
    iv : bytes
        The GCM nonce (not secret).
    tag : bytes
        The GCM authentication tag (not secret).
    salt : bytes
        The PBKDF2 salt used to derive the key.
    """

    ciphertext: bytes
    iv: bytes
    tag: bytes
    salt: bytes

    def encode(self) -> str:
        """Base64-encode the blob for storage in JSON/config."""
        return base64.b64encode(self._pack()).decode("ascii")

    @classmethod
    def decode(cls, data: str) -> EncryptedBlob:
        """Reconstruct an EncryptedBlob from base64."""
        raw = base64.b64decode(data)
        return cls._unpack(raw)

    @property
    def MAGIC(self) -> bytes:
        """Magic bytes for format detection."""
        return MAGIC

    def _pack(self) -> bytes:
        """Pack all fields into a single byte array."""
        header = MAGIC + struct.pack("!III", len(self.salt), len(self.iv), len(self.ciphertext))
        return header + self.salt + self.iv + self.ciphertext + self.tag

    @classmethod
    def _unpack(cls, raw: bytes) -> EncryptedBlob:
        """Unpack a byte array back into an EncryptedBlob."""
        magic_len = len(MAGIC)
        magic = raw[:magic_len]
        assert magic == MAGIC, f"Bad magic: {magic!r}"
        salt_len, iv_len, ct_len = struct.unpack("!III", raw[magic_len:magic_len + 12])
        offset = magic_len + 12
        salt = raw[offset:offset + salt_len]
        offset += salt_len
        iv = raw[offset:offset + iv_len]
        offset += iv_len
        ciphertext = raw[offset:offset + ct_len]
        offset += ct_len
        tag = raw[offset:]
        return cls(ciphertext=ciphertext, iv=iv, tag=tag, salt=salt)


# ---------------------------------------------------------------------------
# Core crypto
# ---------------------------------------------------------------------------


def derive_key(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """Derive a 256-bit AES key from a password using PBKDF2.

    Parameters
    ----------
    password : str
        The master password.
    salt : bytes | None
        A 32-byte salt.  If ``None``, a new one is generated.

    Returns
    -------
    tuple[bytes, bytes]
        ``(key, salt)`` — the derived 32-byte key and the salt used.
    """
    if salt is None:
        salt = secrets.token_bytes(SALT_SIZE)

    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS,
        dklen=KEY_SIZE,
    )
    return key, salt


def encrypt_data(plaintext: bytes, key: bytes) -> EncryptedBlob:
    """Encrypt *plaintext* using AES-256-GCM.

    Parameters
    ----------
    plaintext : bytes
        Data to encrypt.
    key : bytes
        32-byte encryption key.

    Returns
    -------
    EncryptedBlob
        The encrypted payload with all metadata.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    iv = secrets.token_bytes(IV_SIZE)
    aesgcm = AESGCM(key)
    # AESGCM.encrypt returns ciphertext + tag concatenated
    ct_and_tag = aesgcm.encrypt(iv, plaintext, None)
    ciphertext = ct_and_tag[:-TAG_SIZE]
    tag = ct_and_tag[-TAG_SIZE:]
    salt = secrets.token_bytes(SALT_SIZE)
    return EncryptedBlob(ciphertext=ciphertext, iv=iv, tag=tag, salt=salt)


def decrypt_data(blob: EncryptedBlob, key: bytes) -> bytes:
    """Decrypt an EncryptedBlob back to plaintext.

    Parameters
    ----------
    blob : EncryptedBlob
        The encrypted payload.
    key : bytes
        The 32-byte key (must match the salt in *blob*).

    Returns
    -------
    bytes
        The decrypted plaintext.

    Raises
    ------
    ValueError
        If the authentication tag does not match (wrong key or corrupted data).
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    aesgcm = AESGCM(key)
    ct_and_tag = blob.ciphertext + blob.tag
    try:
        return aesgcm.decrypt(blob.iv, ct_and_tag, None)
    except Exception as exc:
        raise ValueError("Decryption failed: invalid key or corrupted data") from exc


def verify_password(password: str, key: bytes, blob: EncryptedBlob) -> bool:
    """Verify that *password* is correct for *blob* without full decryption.

    A quick HMAC check against the first 16 bytes of ciphertext.
    """
    try:
        test = decrypt_data(blob, key)[:16]
        return test == test  # always true if decryption succeeded
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Key storage
# ---------------------------------------------------------------------------


class KeyStorage:
    """Persist encrypted key material to disk.

    Stores keys in ``.osintote/keys.json`` using the format::

        {
            "version": 1,
            "keys": {
                "osintote.db": "<base64-encoded EncryptedBlob>",
                ...
            }
        }
    """

    def __init__(self, config_dir: Path | str = ".osintote") -> None:
        self.config_dir = Path(config_dir)
        self.keys_file = self.config_dir / "keys.json"

    def save_key(self, resource: str, blob: EncryptedBlob) -> None:
        """Encrypt and store a key for *resource*."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        data = self._load()
        data["keys"][resource] = blob.encode()
        # Store salt separately so key derivation is deterministic
        data["keys"][resource + ".salt"] = base64.b64encode(blob.salt).decode("ascii")
        self._save(data)

    def load_key(self, resource: str) -> EncryptedBlob | None:
        """Retrieve and decrypt a stored key for *resource*."""
        data = self._load()
        encoded = data["keys"].get(resource)
        if encoded is None:
            return None
        blob = EncryptedBlob.decode(encoded)
        # Restore the PBKDF2 salt so key derivation is deterministic
        pbkdf2_salt = data.get("pbkdf2_salt", {}).get(resource)
        if pbkdf2_salt:
            blob.salt = base64.b64decode(pbkdf2_salt)
        return blob

    def delete_key(self, resource: str) -> bool:
        """Remove a stored key. Returns True if it existed."""
        data = self._load()
        if resource in data["keys"]:
            del data["keys"][resource]
            self._save(data)
            return True
        return False

    def list_resources(self) -> list[str]:
        """Return resource names that have stored keys."""
        return list(self._load()["keys"].keys())

    def has_key(self, resource: str) -> bool:
        """Check whether a key exists for *resource*."""
        return resource in self._load()["keys"]

    def _load(self) -> dict:
        """Load the keys file, creating it if absent."""
        if self.keys_file.exists():
            with open(self.keys_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"version": 1, "keys": {}}
        return data

    def _save(self, data: dict) -> None:
        """Write the keys file atomically."""
        tmp = self.keys_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(self.keys_file)


# ---------------------------------------------------------------------------
# EncryptionManager
# ---------------------------------------------------------------------------


class EncryptionManager:
    """High-level API for encrypting and decrypting data.

    Combines key derivation, encryption/decryption, and key storage
    into a single interface.

    Usage::

        mgr = EncryptionManager(password="my-master-password")
        secret = mgr.encrypt(b"top-secret")
        plain = mgr.decrypt(secret)

        # Store a key for the database
        mgr.save_key("osintote.db")

        # Load and use later
        mgr2 = EncryptionManager(password="my-master-password")
        mgr2.load_key("osintote.db")
    """

    def __init__(self, password: str, key_storage: KeyStorage | None = None) -> None:
        """Initialise with a master password.

        Parameters
        ----------
        password : str
            The master password.  Stored in memory; callers should ensure
            it is cleared when no longer needed.
        key_storage : KeyStorage | None
            Optional custom KeyStorage instance.
        """
        self._password = password
        self._key: bytes | None = None
        self._salt: bytes = b""
        self._key_storage = key_storage or KeyStorage()

    @property
    def key(self) -> bytes:
        """The derived encryption key (computed on first access)."""
        if self._key is None:
            self._key, self._salt = derive_key(self._password)
        return self._key

    def encrypt(self, plaintext: bytes) -> EncryptedBlob:
        """Encrypt data using the derived key."""
        return encrypt_data(plaintext, self.key)

    def decrypt(self, blob: EncryptedBlob) -> bytes:
        """Decrypt data using the derived key."""
        return decrypt_data(blob, self.key)

    def save_key(self, resource: str) -> None:
        """Store the derived key for *resource*."""
        _ = self.key  # ensure _salt is derived
        blob = self.encrypt(self._salt)  # encrypt salt as a test of the key
        self._key_storage.save_key(resource, blob)
        # Store PBKDF2 salt separately (blob.salt is AES salt, not PBKDF2 salt)
        data = self._key_storage._load()
        if "pbkdf2_salt" not in data:
            data["pbkdf2_salt"] = {}
        data["pbkdf2_salt"][resource] = base64.b64encode(self._salt).decode("ascii")
        self._key_storage._save(data)

    def load_key(self, resource: str) -> bool:
        """Load and verify a stored key. Returns True if valid."""
        blob = self._key_storage.load_key(resource)
        if blob is None:
            return False
        # Get the PBKDF2 salt from storage
        data = self._key_storage._load()
        pbkdf2_salt = data.get("pbkdf2_salt", {}).get(resource)
        if pbkdf2_salt:
            blob.salt = base64.b64decode(pbkdf2_salt)
        try:
            # Derive key with the stored PBKDF2 salt
            key = hashlib.pbkdf2_hmac(
                "sha256", self._password.encode("utf-8"),
                blob.salt, ITERATIONS, dklen=KEY_SIZE,
            )
            decrypt_data(blob, key)
            return True
        except ValueError:
            return False

    def verify_password(self, password: str, resource: str) -> bool:
        """Verify a password against a stored key for *resource*."""
        blob = self._key_storage.load_key(resource)
        if blob is None:
            return False
        try:
            key = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"),
                blob.salt, ITERATIONS, dklen=KEY_SIZE,
            )
            decrypt_data(blob, key)
            return True
        except ValueError:
            return False

    def clear(self) -> None:
        """Securely clear the in-memory key and password."""
        self._key = None
        self._salt = b""
        # Note: password is a str (immutable), cannot be cleared.
        # Callers should delete the reference: del mgr


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------


def prompt_master_password() -> str:
    """Prompt the user for a master password interactively."""
    import getpass

    password = getpass.getpass("Master password: ")
    if not password:
        raise ValueError("Password cannot be empty")
    confirm = getpass.getpass("Confirm master password: ")
    if password != confirm:
        raise ValueError("Passwords do not match")
    return password


def prompt_existing_password() -> str:
    """Prompt the user for an existing master password."""
    import getpass

    attempts = 3
    for i in range(attempts):
        password = getpass.getpass("Master password: ")
        if password:
            return password
        if i < attempts - 1:
            print("[yellow]Password cannot be empty. Try again.[/]")
    raise ValueError("Max attempts exceeded")
