# Core Area Test Coverage Report

This document reports the test coverage status and target gates for the core areas of the LLM Inference Stack codebase.

## Overview & Quality Gates

To ensure code quality in core areas without relying solely on a single global coverage limit, we enforce specific package-level gates. Because several core areas are currently below our ultimate goal of **70%**, we have instituted a **ratchet plan** (defined in `config/coverage-ratchets.json`) to prevent regression while systematically driving coverage upward.

| Core Area | Package Path(s) | Current Coverage | Target Gate | Ratchet Status |
|---|---|---|---|---|
| **core_runtime** | `app/services/runtime`, `app/services/workflows`, `app/services/agents`, `app/services/routing` | **48.42%** | 70.00% | Enforced at 48.40% |
| **governance** | `app/services/governance` | **29.15%** | 70.00% | Enforced at 29.10% |
| **security** | `app/services/security`, `app/services/auth` | **37.33%** | 70.00% | Enforced at 37.30% |
| **financial/billing** | `app/services/billing` | **35.23%** | 70.00% | Enforced at 35.20% |

---

## Detailed Analysis

### 1. core_runtime
- **Current Coverage:** 48.42% (11562 / 23880 lines)
- **Target:** 70.00%
- **Gaps:**
  - `app/services/agents/workflows` is at **36.06%** coverage. Webhook signal triggers and sleeping state transitions are lacking isolated unit-level testing.
  - `app/services/routing/infra_adapters` is at **28.66%** coverage. Proxmox and Nomad adapters are not fully covered.
- **Needed Tests:**
  - Mocked unit tests for Proxmox and Nomad routing adapter initialization and resource reporting.
  - Unit tests covering edge-case signal wakeups and timeouts in workflow orchestrators.

### 2. governance
- **Current Coverage:** 29.15% (360 / 1235 lines)
- **Target:** 70.00%
- **Gaps:**
  - `app/services/governance/policy_engine` is at **25.15%** coverage. Conflict detection for overlapping policy bindings is lightly tested.
- **Needed Tests:**
  - Focused unit tests verifying conflict resolutions and error states under overlapping policy criteria.

### 3. security
- **Current Coverage:** 37.33% (1019 / 2730 lines)
- **Target:** 70.00%
- **Gaps:**
  - Key rotation and attestation challenge mechanisms under `app/services/security/` are missing dedicated unit tests.
- **Needed Tests:**
  - Unit tests mocking hardware attestation challenge validations and rotation triggers.

### 4. financial/billing
- **Current Coverage:** 35.23% (626 / 1777 lines)
- **Target:** 70.00%
- **Gaps:**
  - Payment gateway adapters and billing ledger margin calculations under `app/services/billing` are only covered by high-level integration tests.
- **Needed Tests:**
  - Unit tests mocking payment callback hooks and ledger transaction updates.
