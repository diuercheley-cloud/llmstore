---
owner: platform-ops
status: consolidated
---

# Approval Policies for Agentic HITL

Approval Policies allow administrators to configure dynamic checks and rules that intercept agent tool calls. This document details policy schemas, evaluation orders, and trigger types.

## Policy Schema

Policies are stored in the `agent_approval_policies` table and are structured as follows:

* **`id`**: Unique UUID identifier.
* **`name`**: Descriptive name of the policy (e.g., "Prevent unauthorized file writes").
* **`description`**: Explanation of what the policy accomplishes.
* **`trigger_type`**: Evaluated rule type:
  * `always`: Pauses on every single tool call.
  * `tool_call`: Targets specific tool executions matching `tool_name`.
  * `risk_level`: Evaluated against overall risk thresholds.
* **`tool_name`** (optional): Name of the tool to target when trigger type is `tool_call`.
* **`risk_level_threshold`** (optional): The minimum risk level (`low`, `medium`, `high`, `critical`) required to trigger approval when trigger type is `risk_level`.
* **`required_role`** (optional): The minimum role required for a reviewer (`admin_read`, `admin_write`, `super_admin`). Defaults to `admin_write`.
* **`enabled`** (default: `true`): Toggles whether the policy is active.

---

## Evaluation Precedence & Order

When an agent requests a tool invocation, the system checks for approval requirements in a specific sequence. As soon as a match is found that returns `approval_required = True`, the check stops, and a pending request is created.

```
                   [ Evaluate Tool Call ]
                             │
                             ▼
                (1. Enabled Policies Match?)
                - Type: always
                - Type: tool_call (tool matching)
                - Type: risk_level (risk >= threshold)
                             │
                Yes ─────────┴─────────► [ Trigger Approval ]
                 │
                 No
                 ▼
         (2. Lifecycle Governance Override?)
         - Agent Registry Entry has human_approval_required = true
                 │
                Yes ───────────────────► [ Trigger Approval ]
                 │
                 No
                 ▼
          (3. Explicit Tool Registry Rules?)
          - Tool definition has requires_approval = true
          - Tool side_effect_level is 'write' or 'destructive'
                 │
                Yes ───────────────────► [ Trigger Approval ]
                 │
                 No
                 ▼
        (4. Global High Risk Safeguards?)
        - AGENT_APPROVAL_REQUIRED_FOR_HIGH_RISK = true AND
          Run risk (max of agent/registry/tool) is high/critical
                 │
                Yes ───────────────────► [ Trigger Approval ]
                 │
                 No
                 ▼
          [ Proceed to Tool Execution ]
```

---

## Policy Trigger Types

### 1. Always Trigger
An `always` trigger is useful for strict auditing, sandbox modes, or staging environments where every tool action must be inspected.
* **Example Setup**:
  * `name`: "Sandbox Mode Audit"
  * `trigger_type`: "always"
  * `required_role`: "admin_write"

### 2. Tool-Specific Trigger (`tool_call`)
Triggers approval only when a specific tool (e.g., `execute_sql`, `delete_user`, `send_email`) is called. This is the preferred method for guarding specific sensitive API interfaces.
* **Example Setup**:
  * `name`: "Guard Send Email"
  * `trigger_type`: "tool_call"
  * `tool_name`: "send_email"
  * `required_role`: "admin_write"

### 3. Risk-Based Trigger (`risk_level`)
Triggers approval if the overall risk of the execution meets or exceeds a specific threshold. The overall risk is calculated as the **maximum** risk level configured among:
1. The **Agent Definition** risk (`low`, `medium`, `high`, `critical`).
2. The **Agent Registry Entry** risk.
3. The **Tool Definition** risk.

If this calculated risk is greater than or equal to `risk_level_threshold`, the policy triggers.
* **Example Setup**:
  * `name`: "Guard Critical Tools"
  * `trigger_type`: "risk_level"
  * `risk_level_threshold`: "high"
  * `required_role`: "super_admin"
