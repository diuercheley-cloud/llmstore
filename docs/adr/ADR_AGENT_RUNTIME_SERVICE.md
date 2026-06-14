# ADR: Agent Runtime Independent Microservice

## Status
Proposed

## Context
The current agent runtime is tightly coupled within the `control_plane`. This increases the complexity of the control plane and prevents independent scaling of the agent execution logic, which is CPU and I/O intensive. As the number of agent runs grows, we need to be able to scale the execution plane separately from the API management plane.

## Decision
Extract the agent runtime into a dedicated microservice: `agent-runtime-service`.

### 1. Communication Protocol
- **Internal Client (Control Plane to Agent Runtime)**: REST API (FastAPI) for synchronous control (start, pause, resume, cancel).
- **Asynchronous Events**: Redis-based task queue for execution jobs (maintaining compatibility with the current `AgentQueueManager`).
- **Data Sharing**: Shared database (Postgres) for now to minimize migration effort, moving towards shared schemas/contracts for data persistence.

### 2. Authentication & Security
- **M2M Authentication**: Control Plane will use a dedicated internal API token to communicate with the Agent Runtime service.
- **Tenant Isolation**: Tenant ID must be passed in every request and strictly enforced by the Agent Runtime service.

### 3. Reliability & Fault Tolerance
- **Retries**: The internal client in the Control Plane will implement exponential backoff for transient failures.
- **Idempotency**: All run-start requests will support idempotency keys (provided by the Control Plane).
- **Health Checks**: The new service will expose `/health` and `/ready` endpoints.

### 4. Migration Strategy
- **Phase 1 (Skeleton)**: Create the new service package and define the API contract.
- **Phase 2 (Internal Client)**: Implement an internal client in the Control Plane that can switch between "in-process" (legacy) and "remote" (service) modes using a feature flag `AGENT_RUNTIME_SERVICE_REMOTE=true`.
- **Phase 3 (Extraction)**: Move the business logic from `control_plane/app/services/agents/` to the new service, keeping thin wrappers in the Control Plane for backward compatibility.

## Consequences
- **Pros**:
    - Independent scaling of execution workloads.
    - Reduced complexity in the Control Plane.
    - Better isolation of runtime failures.
- **Cons**:
    - Increased operational complexity (deploying/monitoring an extra service).
    - Network latency for control operations (minimal compared to LLM latency).
