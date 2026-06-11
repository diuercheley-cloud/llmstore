# Backup Architecture

## Overview

The LLM Inference Stack provides a multi-layered backup system. This document
describes the official `BackupService` (production-grade, encrypted, signed),
the legacy `AgentBackupService` (deprecated), and the shell-based scripts
that complement them.

---

## Compatibility Matrix

| # | Mechanism | Status | Coverage | Replacement |
|---|-----------|--------|----------|-------------|
| 1 | `BackupService` (`app.services.backup.backup_service`) | **Official** | Full system: DB, configs, feature flags, agent models, workflows, audit chain | — |
| 2 | `BackupService` + `RestoreStagingService` | **Official** | Safe restore with staging + rollback | — |
| 3 | `AgentBackupService` (`app.services.disaster_recovery.agent_backup`) | **DEPRECATED** v2.4+ | Agent configs, memory, runs only | `BackupService` with `scope=logical-agent-backup` |
| 4 | `scripts/backup/backup.sh` | **Official** | Production pg_dump + config + manifest | — |
| 5 | `scripts/backup/restore.sh` | **Official** | Production pg_restore + checksums | — |
| 6 | `scripts/backup/backup-local.sh` | **Official** | Local dev pg_dump + .env sanitize | — |
| 7 | `scripts/backup/restore-local.sh` | **Official** | Local dev pg_restore | — |
| 8 | `scripts/backup/create_backup.py` | **Official** | API-triggered backup creation | — |
| 9 | `scripts/backup/restore_backup.py` | **Official** | API-triggered dry-run restore | — |
| 10 | `scripts/backup/verify_backup.py` | **Official** | API-triggered integrity verification | — |
| 11 | `scripts/backup/redact_json.py` | **Official** | Sensible data redaction (YAML/JSON/.env) | — |
| 12 | `scripts/backup/retention-local.sh` | **Official** | Local retention policy execution | — |
| 13 | CLI `llmstack backup` (`scripts/llm_harness/stack_cli.py`) | **Official** | CLI-triggered backup via `POST /admin/backup` | — |
| 14 | CLI `llmstack restore` | **Official** | CLI-triggered restore via API | — |
| 15 | CLI `llmstack backups` | **Official** | CLI-triggered backup listing | — |
| 16 | `BackupScheduler` (`agent_backup.py`) | **DEPRECATED** v2.4+ | Periodic agent-only backups | Use `cron` + `llmstack backup` |
| 17 | `scripts/backup/clean-rag-local-data.sh` | **Official** | RAG data cleanup | — |
| 18 | `scripts/backup/clean-compose-local.sh` | **Official** | Docker Compose cleanup | — |
| 19 | `scripts/backup/cleanup-local-branches.sh` | **Official** | Git branch cleanup (git maintenance) | — |

---

## Mechanism details

### 1. `BackupService` (official)

**Location:** `control_plane/app/services/backup/backup_service.py`

Capabilities:
- Full system backup: database dump, configuration files, feature flags, agent
  models, workflow models, embedding models
- Fernet encryption (`cryptography.fernet`)
- HMAC-SHA256 signing
- Sensitive-key redaction (tokens, secrets, passwords, keys, credentials)
- Immutable audit event logging
- `logical-agent-backup` scope (replaces `AgentBackupService`)

**Endpoints (FastAPI router `admin_backup_router`):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/admin/backup` | Create backup |
| GET | `/admin/backup` | List backups |
| GET | `/admin/backup/{id}` | Get backup manifest |
| GET | `/admin/backup/{id}/verify` | Verify integrity |
| POST | `/admin/backup/{id}/verify` | Verify integrity |
| POST | `/admin/backup/{id}/restore` | Restore (blocked in production without dry-run) |
| POST | `/admin/backup/{id}/restore/dry-run` | Dry-run restore |
| GET | `/admin/backup/{id}/status` | Backup status |
| POST | `/admin/backup/audit/verify` | Verify audit chain |
| POST | `/admin/backup/restore-requests` | Create restore request (approval workflow) |
| POST | `/admin/backup/restore-requests/{id}/approve` | Approve restore request |
| POST | `/admin/backup/restore-requests/{id}/execute` | Execute approved restore |

### 2. RestoreStagingService (official)

**Location:** `control_plane/app/services/backup/restore_staging_service.py`

Safe restore flow:
1. Validate manifest, signature, checksums
2. Create staging database environment
3. Restore to staging
4. Validate schema, alembic head, component tables
5. Create pre-restore safety backup
6. Promote to production (skip in dry-run)
7. Automatic rollback via safety backup if promotion fails
8. Clean up staging environment

### 3. AgentBackupService (DEPRECATED)

**Location:** `control_plane/app/services/disaster_recovery/agent_backup.py`

**Status:** Deprecated since v2.4 — will be removed in v3.0.

Replaced by `BackupService` with `scope=logical-agent-backup`.

The `AgentBackupService` performed unencrypted, unsigned tar.gz backups of
agent configurations, memory items, and run history. It did not support
integrity verification, encryption, or immutable audit logging.

**Migration:** Use `POST /admin/backup` with `{"scope": "logical-agent-backup"}`.

### 4. Shell scripts (`scripts/backup/`)

Shell scripts handle raw file-system and pg_dump/pg_restore operations.
They operate independently of the Python service layer:

| Script | Purpose |
|--------|---------|
| `backup.sh` | Production: pg_dump, config, optional models/RAG, GPG encryption |
| `restore.sh` | Production: checksum verify, alembic check, pg_restore |
| `backup-local.sh` | Local dev: pg_dump, .env sanitization |
| `restore-local.sh` | Local dev: dry-run, checksum, RAG/model file restore |
| `create_backup.py` | API-triggered: `POST /admin/backup` |
| `restore_backup.py` | API-triggered: `POST /admin/backup/{id}/restore/dry-run` |
| `verify_backup.py` | API-triggered: `GET /admin/backup/{id}/verify` |
| `redact_json.py` | Redact sensitive fields from JSON/YAML/.env |
| `retention-local.sh` | Local retention: RAG, TTS, logs, backups cleanup |

### 5. CLI (`llmstack`)

**Location:** `scripts/llm_harness/stack_cli.py`

| Command | HTTP method | API path |
|---------|-------------|----------|
| `llmstack backup --logical-agent-backup` | POST | `/admin/backup` |
| `llmstack restore <id> --dry-run` | POST | `/admin/backup/{id}/restore` |
| `llmstack backups` | GET | `/admin/backup` |

---

## Precedence and consistency

1. **API is the single source of truth** for backup creation, verification, and restore.
2. Shell scripts are for **offline / emergency** scenarios where the API is unavailable.
3. `AgentBackupService` is **deprecated** — all new code must use `BackupService`.
4. The `scripts/backup/` Python scripts (`create_backup.py`, `restore_backup.py`,
   `verify_backup.py`) call the **same API** as the CLI — they are thin wrappers.

---

## URL path conventions

| Component | Correct base URL | Example full path |
|-----------|-----------------|-------------------|
| Python scripts (`scripts/backup/`) | `http://localhost:8000` | `/admin/backup` |
| CLI (`llmstack`) | `http://localhost:8080` | `/admin/backup` |
| Frontend API client | `http://localhost:8080` | `/admin/backup` |

All API paths use the router prefix `/admin/backup` (not `/api/admin/backup`).

---

## Future roadmap

| Version | Change |
|---------|--------|
| v2.4 | `AgentBackupService` marked deprecated |
| v2.5 | `BackupScheduler` removed; cron-based scheduling recommended |
| v3.0 | `agent_backup.py` module removed |
| v3.0 | All scripts consolidated under `scripts/backup/` using API exclusively |
