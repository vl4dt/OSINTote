# Security

Security considerations, threat model, and hardening recommendations for OSINTote.

## Threat Model

### Actors

| Actor | Capabilities | Goals |
|-------|-------------|-------|
| **Attacker** | External network access | Access sensitive data, manipulate results |
| **User** | Application access | Protect own intelligence data |
| **Admin** | Full system access | Maintain system integrity |

### Assets

- **API Keys** — Encrypted with AES-256-GCM using PBKDF2-derived keys
- **Database** — SQLite file containing targets, tasks, and collected records
- **Web UI** — SvelteKit application served via Uvicorn
- **Callbacks** — Shell commands and webhook URLs configured by users

## Encryption

### Data at Rest

All sensitive data is encrypted using AES-256-GCM:

- **API Keys**: Encrypted before storage in SQLite
- **Webhook Secrets**: Stored encrypted
- **Encryption Keys**: Derived via PBKDF2 with 600,000 iterations

### Key Management

```
User Password → PBKDF2(salt, 600k iterations) → AES-256 Key
                                               → HMAC-SHA256 tag
```

The salt is stored alongside the ciphertext. The key is persisted as an encrypted blob with a built-in integrity tag.

## Recommendations

### Production Deployment

1. **Use HTTPS** — Deploy behind a reverse proxy (nginx, Caddy) with TLS
2. **Bind to localhost** — Set `listen_host=127.0.0.1` and use port forwarding for remote access
3. **Set a password** — Implement authentication before exposing to untrusted networks
4. **Rotate encryption keys** — Regenerate the master key periodically
5. **Use external database** — Migrate from SQLite to PostgreSQL for production
6. **Restrict webhook URLs** — Use network segmentation to limit callback destinations

### Hardening

```bash
# Set database to a non-default path (harder to find)
osintote init --db-path /var/data/osintote.db

# Use force mode to ensure config is written securely
osintote init --force
```

### Webhook Security

All webhooks are signed with HMAC-SHA256:

```
X-Webhook-Signature: sha256=<hexdigest>
```

Recipients should verify the signature before processing the payload.

## Known Limitations

- **Authentication**: No built-in auth system (planned for future release)
- **RBAC**: No role-based access control (single-user design)
- **Audit Logging**: Event logging is structured but not tamper-evident
- **TLS**: The Uvicorn server does not support TLS directly; use a reverse proxy

## Reporting Vulnerabilities

Please report security vulnerabilities privately to the repository maintainers. Do not open public issues for security-sensitive findings.
