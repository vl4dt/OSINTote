# ADR-002: Encryption Strategy

**Status**: Accepted
**Date**: 2026-05-28

## Context

OSINTote stores sensitive data (API keys, webhook secrets, encryption keys) in a local SQLite database. We needed a strategy for encrypting this data at rest.

## Decision

Use **AES-256-GCM** for symmetric encryption with **PBKDF2** for key derivation.

### Components

- **AES-256-GCM**: Authenticated encryption providing both confidentiality and integrity
- **PBKDF2**: Key derivation with 600,000 iterations (OWASP 2024 recommendation)
- **HMAC-SHA256**: Integrity tag for the encrypted key blob
- **PBKDF2 salt**: Separate 16-byte salt stored alongside the ciphertext for deterministic key derivation

### Implementation

```python
class EncryptedBlob:
    MAGIC = b'OSINT'
    # Layout: MAGIC + iv(12) + tag(16) + ciphertext
    
class KeyStorage:
    # Stores the PBKDF2 salt alongside the AES key
    pbkdf2_salt: bytes
    encrypted_key: EncryptedBlob

class EncryptionManager:
    # Derives key from password, manages KeyStorage, persists to disk
```

## Alternatives Considered

- **Argon2id**: Better than PBKDF2 against GPU attacks, but adds a C dependency
- **NaCl/libsodium**: Well-audited, but adds an external dependency
- **Python cryptography library**: Chosen — widely used, well-maintained, no C deps beyond the underlying OpenSSL bindings

## Consequences

- **Positive**: Strong encryption, self-contained, no external crypto services needed
- **Negative**: Password-based encryption means losing the password loses all encrypted data
- **Mitigation**: Document the trade-off; consider a key escrow mechanism in a future release
