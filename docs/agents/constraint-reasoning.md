# Constraint-Based Reasoning

## Overview
Constraint-Based Reasoning enables agents to validate and optimize their execution plans against formal mathematical or logical restrictions. This ensures that agentic workflows adhere to strict organizational policies, resource limits, and scheduling requirements.

## Key Capabilities
- **Formal Validation**: Integrates with solvers like **Z3 (SMT)** and **GLPK (Linear Programming)** to prove plan satisfiability.
- **Rule-Based Fallback**: Provides a simple `ConstraintValidator` that checks field-level constraints when full solvers are unavailable or unnecessary.
- **Blocking Enforcement**: Any plan that violates a mandatory constraint is blocked from execution, preventing costly or unsafe operations.

## Common Use Cases
1. **Budget Allocation**: Ensuring total spend across multiple steps does not exceed a hard cap.
2. **Scheduling**: Validating that time-sensitive tasks fit within a specific window (SLAs).
3. **Resource Management**: Checking availability of specialized tools or compute clusters before initiating a run.
4. **SLA/SLO Compliance**: Proving that the chosen path meets performance and reliability guarantees.

## Constraint Model
Constraints are defined using the `ConstraintModel`, which supports:
- **Operators**: `eq`, `neq`, `gt`, `lt`, `ge`, `le`, `in`.
- **Types**: Comparison, Arithmetic, Logic, and Resource-based checks.

## Configuration
- `AGENT_CONSTRAINT_REASONING_ENABLED`: Master switch for the subsystem.
- `AGENT_Z3_SOLVER_ENABLED`: Enables SMT-based formal proofing.
- `AGENT_GLPK_SOLVER_ENABLED`: Enables linear programming optimization.

## Usage
Validated plans include a status and, where supported by the solver, a proof of satisfaction or a detailed `unsat` reason explaining why the plan was rejected.
