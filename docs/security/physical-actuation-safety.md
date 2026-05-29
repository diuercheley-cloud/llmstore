# Physical Actuation Safety

## Governance Posture
Interacting with the physical world introduces unique risks that require a conservative security posture. The platform implements multiple layers of protection to ensure that AI agents never perform unsafe physical actions.

### 1. Global Actuation Interlock
By default, the `AGENT_PHYSICAL_ACTUATION_ENABLED` flag is set to `false`. When disabled, the `DigitalTwinService` will block all outgoing commands, regardless of their content or the agent's permissions.

### 2. Digital Twin Safety Boundaries
Each twin can have predefined safety boundaries (e.g., min/max pressure, voltage limits). The `SafetyInterlock` service enforces these boundaries at the API level. Any command exceeding these limits is immediately rejected and triggers a `critical` safety event.

### 3. Dangerous Pattern Detection
The system identifies and blocks "dangerous patterns," such as:
- Rapid oscillation of critical valves.
- Overriding emergency stop signals.
- Factory reset attempts in production environments.

### 4. Human-in-the-Loop (HITL) for Actuation
All physical actuation commands in production environments require a `human_signature`. The agent run is paused until an authorized operator reviews the command's purpose and approves the execution.

### 5. Compensation and Rollback
Where the underlying protocol supports it, connectors are encouraged to provide "compensation actions" that can revert the physical state in case of failure or unintended divergence.
