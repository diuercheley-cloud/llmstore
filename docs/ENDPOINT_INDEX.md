---
owner: platform-ops
status: consolidated
---

# Endpoint Index: API Catalog

This document lists the primary API endpoints categorized by module and access level.

## 1. Public API (OpenAI Compatible)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/chat/completions` | OpenAI-compatible chat completion |
| POST | `/v1/completions` | Legacy completion support |
| GET | `/v1/models` | List available models for the tenant |

## 2. Admin API (Control & Governance)
### Inference & Trust
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/inference/receipts` | List inference receipts |
| GET | `/admin/inference/proofs/timelines` | List Merkle timelines |
| POST | `/admin/inference/proofs/timelines/build` | Build a new timeline window |
| POST | `/admin/inference/proofs/timelines/{id}/seal` | Seal a timeline (immutable) |
| GET | `/admin/inference/proofs/proofs` | List execution proofs |

### Routing & Traffic
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/routing/backends` | List model backends |
| POST | `/admin/routing/traffic-shift` | Globally shift traffic between providers |
| GET | `/admin/routing/cross-cluster` | Manage cross-cluster forwarding |

### Billing & Revenue
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/billing/reconciliation` | Financial reconciliation dashboard |
| GET | `/admin/revenue/protection` | Revenue protection anomalies |
| POST | `/admin/wallets/{id}/topup` | Manually top up a client wallet |

## 3. Portal API (Tenant Self-Service)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/portal/usage` | Current month usage stats |
| GET | `/portal/inference/proofs/proofs` | List tenant-safe execution proofs |
| GET | `/portal/inference/proofs/proofs/{id}/export` | Export sanitized proof bundle |
| GET | `/portal/wallet/balance` | Current prepaid wallet balance |
| POST | `/portal/wallet/topup/pix` | Generate PIX copy-paste for topup |

## 4. System & Infrastructure
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Liveness/Readiness probe |
| GET | `/admin/ha/leader` | Current cluster leader status |
| GET | `/admin/infra/executions` | List infrastructure execution tasks |

---

**Next Steps**: See [archive/deprecated/MIGRATION_INDEX.md](archive/deprecated/MIGRATION_INDEX.md) for historical schema notes.
