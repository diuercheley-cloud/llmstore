# Agent Studio GA Graduation

## Overview
Agent Studio has graduated to General Availability (GA), providing a robust environment for designing, validating, and deploying agentic workflows.

## Key Enhancements
1. **Visual Flow Editor**: A comprehensive drag-and-drop interface for building complex agent behaviors.
2. **DAG Validation**: Integrated cycle detection and terminal node validation to ensure execution reliability.
3. **Version Control**: Full support for flow versioning, allowing operators to save iterations and promote specific versions to active status.
4. **Compiler**: A high-fidelity compiler that translates visual designs into standard `AgentPlan` or `Workflow` objects.
5. **Dry-Run Environment**: A side-effect-free execution environment for testing flows with real input data before production rollout.

## Compliance and Governance
- **Policy Pre-checks**: The studio identifies high-risk nodes (e.g., shell execution) and enforces approval requirements before the flow can be saved or compiled.
- **Tenant Isolation**: Flows and their versions are strictly scoped to the owner's `tenant_id`.
- **Traceability**: Every dry-run generates a detailed debug trace stored in `agent_debug_events`.
