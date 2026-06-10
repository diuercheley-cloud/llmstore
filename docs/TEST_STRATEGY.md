# Test Strategy

## Objective
Shift from "testing for volume" to "testing for reliability" by prioritizing high-value, high-fidelity test scenarios over high-mock, low-value tests.

## Marker Policy
All tests MUST be marked with one of the following official markers to be executed in CI:
- `unit`: Isolated, fast, no infrastructure.
- `integration`: Real or realistically simulated infrastructure (DB, Network).
- `contract`: API interface/schema consistency.
- `e2e`: Full system flow validation.
- `smoke`: Essential path verification.
- `security`: Security-critical validation (RBAC, Auth, Encryption).
- `release_gate`: Mandatory for production release.
- `cosmetic`: High-mock, low-value tests (non-blocking, slated for replacement).

## Marker Enforcement
- Tests missing these markers will be excluded or marked as failures in the release gate.
- Marker inference based on file names is strictly prohibited.

## Critical Service Map (P0/P1)
- **Identity/Auth**: Needs `contract` and `security` markers.
- **Billing/Payments**: Needs `integration` markers.
- **Provider Routing**: Needs `integration` markers.
- **Agent Execution**: Needs `e2e` and `integration` markers.
- **Core Config**: Needs `unit` markers.
- **Migrations**: Needs `integration` markers.
- **Audit/Security**: Needs `security` and `release_gate` markers.
