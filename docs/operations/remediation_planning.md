---
owner: platform-ops
status: consolidated
---

# Operational Remediation Planning

## Introduction
The Remediation Planning system provides a structured, deterministic approach to handling potential operational failures. By analyzing signals from various domains, the system proposes a series of steps to mitigate risks and restore stability.

## Planning Workflow
1. **Trigger:** A failure forecast, critical risk assessment, or high-confidence correlation is identified.
2. **Proposal:** The `DeterministicRemediationPlanner` is invoked via the Admin API to generate a plan.
3. **Analysis:** The `BlastRadiusService` and `ApprovalRequirementService` analyze the proposed plan to determine its impact and necessary governance steps.
4. **Receipt:** A `RemediationPlanReceipt` is generated to provide a verifiable record of the planning process.
5. **Review:** Operations teams review the proposed plan and steps in the Admin Dashboard.

## Deterministic Heuristics
The planner uses a set of stable heuristics to ensure consistent outputs:
- **Containment First:** Always prioritize isolating the affected domain to prevent "blast-through" propagation.
- **Ordered Restoration:** Mitigation and recovery steps are ordered logically to minimize side effects.
- **Validation Step:** Every plan concludes with a validation step to ensure the system has returned to a healthy state.
- **Risk-Based Approvals:** Plans with `critical` risk or `high` blast radius automatically trigger executive approval requirements.

## Blast Radius Definitions
- **Low:** Affects a single sub-component or domain with minimal external impact.
- **Medium:** Affects a primary domain or multiple sub-components.
- **High:** Affects multiple primary domains or critical system paths.
- **Critical:** Potential for system-wide failure or significant data integrity risk.

## Limitations
- **No Automatic Execution:** This system DOES NOT execute any of the proposed actions.
- **Advisory Nature:** All plans must be manually reviewed and executed by qualified personnel.
- **Dry-Run Only:** The system assumes a dry-run state for all proposed activities.
