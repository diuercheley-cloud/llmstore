---
owner: platform-ops
status: consolidated
---

# Human-in-the-Loop (HITL) for Agents

This document describes the Human-in-the-Loop (HITL) architecture and policies in the `llm-inference-stack`, designed to pause agent executions at critical or high-risk moments and await human reviewer decisions.

## Conceptual Overview

Robust agent runtimes support pause and resume functionality with persisted state (checkpoints) to allow human intervention. In `llm-inference-stack`, the agent executor intercepts tool calls and checks them against approval policies, registry configurations, and risk levels. If an approval is required, execution is suspended, state is preserved, and a review request is queued.

```
                  [ Agent Run Starts ]
                           │
                           ▼
                  [ Next Step Decision ]
                           │
                     (Tool Call?)
                     /          \
                   Yes           No ──► [ Complete Run ]
                     │
         [ Check Approval Policies ]
                     │
             (Approval Required?)
             /                 \
           Yes                  No ──► [ Execute Tool ]
            │
            ▼
   [ Save Checkpoint ]
   [ Status: waiting_approval ]
   [ Create ApprovalRequest ]
   [ Pause Loop ]
            │
            ▼
    (Human Review) ──────────────────────────┐
      /      │       \                       ▼
  Approve  Reject  Request Changes      [ Expiration Timeout ]
    │        │       │                       │
    │        │       └─► [ Status: paused ]  └─► [ Status: expired ]
    │        │                                   [ Run: failed ]
    │        └─► [ Status: rejected ]
    │            [ Run: failed ]
    ▼
[ Status: approved ]
[ Retrieve raw_tool_input ]
[ Execute Tool ]
[ Resume Loop ]
```

---

## Feature Flags

The system behavior is controlled by the following environment variables (defined in `Settings`):

* **`AGENT_HUMAN_APPROVAL_ENABLED`** (default: `true`):
  Toggles the overall HITL approval capability. If set to `false`, no tool invocations will trigger a pause, regardless of policies.
* **`AGENT_APPROVAL_REQUIRED_FOR_HIGH_RISK`** (default: `true`):
  Enforces mandatory approval for any execution matching a risk level of `high` or `critical` (defined on the agent definition, tool definition, or registry entry).
* **`AGENT_APPROVAL_TIMEOUT_SECONDS`** (default: `86400` / 24 hours):
  Determines the time limit for pending approval requests before the system automatically expires the request and terminates the run as a fail-safe.

---

## Approval Request Schema

Approval requests are recorded in `agent_approval_requests` with the following attributes:

* `id`: Unique UUID of the approval request.
* `agent_run_id`: UUID of the associated run.
* `task_id` (optional): Reference to an orchestration task.
* `tool_invocation_id` (optional): ID of the tool call.
* `risk_level`: The computed overall risk level (`low`, `medium`, `high`, `critical`).
* `reason`: Detailed string describing why the approval was triggered (e.g., policy match, high-risk override).
* `requested_by`: System actor that requested the approval (defaults to `"agent_executor"`).
* `reviewer_role`: Minimum RBAC role required to review (`admin_read`, `admin_write`, `super_admin`).
* `status`: Current status of the request (`pending`, `approved`, `rejected`, `expired`, `cancelled`).
* `expires_at`: Timestamp indicating when the request expires.
* `sanitized_context`: Dictionary containing redacted tool input details for the reviewer UI.
* `decision_reason` (optional): Comments/reason supplied by the reviewer.
* `decided_by` (optional): Name/email of the reviewer.
* `decided_at` (optional): Timestamp of the decision.

---

## Security & Redaction Rules

To protect data privacy and credentials:
1. **Unsanitized Payload**: The original input data is stored in the database column `raw_tool_input`, which is hidden from all API endpoints and only accessible by the server-side agent executor during resumption.
2. **Sanitized Context**: The field `sanitized_context` is generated recursively to redact keys matching sensitive names:
   * Redacts: `prompt`, `secret`, `token`, `password`, `key`, `auth`, `instructions`, `credential`, `signature`, `private`.
   * Truncates long string values (exceeding 500 characters) to avoid bloating the context log while preserving enough details for a decision.

---

## Administrative API Endpoints

All admin endpoints require an active `X-Admin-Token` with appropriate RBAC roles.

* **`GET /admin/agent-approvals`**:
  Lists approval requests (supports pagination and filtering by `status`). Checks and applies expirations on-the-fly.
* **`GET /admin/agent-approvals/{id}`**:
  Fetches detailed metadata of a specific request.
* **`POST /admin/agent-approvals/{id}/approve`**:
  Approves the request, records the decision, triggers audit events, and resumes the execution loop.
* **`POST /admin/agent-approvals/{id}/reject`**:
  Rejects the request, records the decision, triggers audit events, and terminates the run as `failed`.
* **`POST /admin/agent-approvals/{id}/request-changes`**:
  Cancels the request, records the decision, and sets the run status to `paused` for user remediation.

---

## Audit Logs

Every review action (approvals, rejections, change requests, and expirations) triggers a secure audit event using `record_admin_audit_event`:
* Event types: `agent.approval.approved`, `agent.approval.rejected`, `agent.approval.request_changes`.
* Captures actor credentials, timestamp, request ID, target run, and decisions.
