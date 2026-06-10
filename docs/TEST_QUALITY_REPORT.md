# Test Quality Report

## Overview
This report maps test quality to critical services (P0/P1). We are shifting from pure coverage metrics to assessing test reliability, coverage of real failure modes, and elimination of "cosmetic" (high-mock, low-value) tests.

## Test Strategy Reference
See [Test Strategy](TEST_STRATEGY.md) for official marker definitions and our new reliability-focused testing policy.

## Critical Service Map (P0/P1)
| Service | Criticality | Coverage Focus |
| :--- | :--- | :--- |
| **Identity/Auth** | P0 | Contract & Security |
| **Billing/Payments** | P0 | Integration (Real/Mocked DB) |
| **Provider Routing** | P0 | Integration (Real/Mocked Provider) |
| **Agent Execution** | P0 | End-to-end / Integration |
| **Core Config** | P1 | Unit / Precedence Testing |
| **Migrations** | P1 | Integrity / Integration |
| **Audit/Security** | P0 | Security Marker / Integration |

## Audit Methodology
Tests are classified as:
1. **Real Validation**: Tests against real or realistically simulated infrastructure (DB, Network, LLM Gateway).
2. **Partial Validation**: Tests with partial mocking (DB mocked, but API logic real).
3. **Cosmetic**: High-mock/low-value tests that do not validate meaningful behavior.
