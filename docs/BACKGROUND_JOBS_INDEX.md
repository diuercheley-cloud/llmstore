# Background Jobs Index: Asynchronous Workers

This document lists the background loops and periodic tasks responsible for system maintenance, billing, and security.

## 1. Core Maintenance Loops
| Task | Frequency | Description |
|------|-----------|-------------|
| **Usage Sync** | Every 1 min | Syncs cached usage from Redis to PostgreSQL |
| **Leader Election** | Every 10s | Ensures high availability via Redis lock |
| **Health Check** | Every 30s | Probes model providers for availability |

## 2. Billing & Financials
| Task | Frequency | Description |
|------|-----------|-------------|
| **Wallet Thresholds** | Every 5 min | Checks for low balance and sends notifications |
| **PIX Expire** | Every 10 min | Cleans up unpaid/expired PIX topup requests |
| **Financial Recon** | Daily (00:00) | Aggregates daily costs and computes margins |

## 3. Security & Trust Chain
| Task | Frequency | Description |
|------|-----------|-------------|
| **Merkle Sealing** | Configurable | Seals current timeline window (if auto-seal enabled) |
| **Runtime Audit** | Every 15 min | Re-verifies runtime integrity tokens of active nodes |
| **Receipt Chaining** | Every 1 min | Validates the integrity of the latest receipt hash chain |

## 4. Traffic & Routing
| Task | Frequency | Description |
|------|-----------|-------------|
| **Geo-IP Sync** | Weekly | Updates local Geo-IP database for routing accuracy |
| **Latency Monitor** | Real-time | Aggregates provider latency for profit/speed routing |
| **Infra Exec** | Event-driven | Processes pending infrastructure deployment tasks |

## 5. Implementation Notes
- **Worker Process**: Most jobs run in the `control_plane` main process or a dedicated `celery` worker pool.
- **Locking**: Redis is used to ensure tasks don't overlap across multiple Control Plane nodes.
- **Logging**: Job failures are logged to the `admin_audit_logs` table.

---

**Next Steps**: Return to [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md) for the big picture.
