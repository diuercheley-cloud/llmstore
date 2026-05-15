# Migration Index: Database Evolution

This document tracks the database schema evolution through Alembic migrations.

## Recent Phase-Specific Migrations (2026)

| Revision | Date | Description | Module |
|----------|------|-------------|--------|
| `b42f7e3a1d9c` | 2026-05-15 | Phase 42: Merkle Audit Timelines | Auditing |
| `f899d30584c3` | 2026-05-15 | Phase 21.1: Infra Simulation | Infrastructure |
| `20260515_0060` | 2026-05-15 | Verifiable Execution Proofs | Auditing |
| `20260515_0059` | 2026-05-15 | Cryptographic Inference Receipts | Auditing |
| `20260515_0058` | 2026-05-15 | Inference Reproducibility | Auditing |
| `20260515_0057` | 2026-05-15 | Runtime Model Integrity | Security |
| `20260515_0056` | 2026-05-15 | Model Supply Chain | Security |
| `20260515_0055` | 2026-05-15 | Sovereign Airgap Governance | Compliance |
| `20260514_0054` | 2026-05-14 | Tenant Encryption Controls | Security |
| `20260514_0053` | 2026-05-14 | Multi-Region Governance Federation | Compliance |

## Core Infrastructure Migrations

| Revision | Description | Module |
|----------|-------------|--------|
| `3454d3bb899b` | Phase 21: Capacity Planning | Resource Mgmt |
| `aa5096efa31a` | Commercial Canary Promotion Fields | Marketing/DevOps |
| `e96571d94193` | Admin Audit Logs | Security |
| `c93fcfd07a5d` | Sales CRM Models | Business |
| `9c33d5ddfc71` | Merge TTS and API Key heads | System |
| `9eb5fc4a28bd` | API Key Field Extensions | Auth |

## Historical Notes

- **Initial Setup**: Migration of basic tenants, users, and usage tables.
- **Billing V2**: Transition from simple usage counts to prepaid wallets and PIX.
- **Routing V3**: Implementation of geo-aware and profit-aware routing tables.

---

**Next Steps**: See [BACKGROUND_JOBS_INDEX.md](BACKGROUND_JOBS_INDEX.md) for asynchronous process details.
