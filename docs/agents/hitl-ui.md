# Human-in-the-Loop (HITL) UI

The HITL UI provides a centralized interface for administrators to review, approve, and manage critical agent actions.

## Key Features

### 1. Approval Inbox
- View all pending approval requests.
- Filter by **Risk Level** (Low, Medium, High, Critical).
- Filter by **Tenant** or **Agent**.
- Track **Expiration** timers.

### 2. Request Details
- **Sanitized Context**: View tool names and inputs with sensitive data automatically redacted.
- **Reasoning**: See why the agent requested approval (e.g., high-risk tool call, policy match).
- **Decision Actions**: Approve, Reject, or Request Changes.

### 3. Batch Approval
- Efficiently process multiple **Low Risk** requests simultaneously.
- High-risk or critical requests are automatically excluded from batch actions to ensure individual oversight.

### 4. Escalation Paths
- **Timeout Escalation**: Automatically promotes a request to a higher role (e.g., Super Admin) if it remains pending near its expiration.
- **High Risk Promotion**: Critical risk requests can be automatically escalated for senior review.

## Security and RBAC

- **Sanitization**: All context shown in the UI is deep-scrubbed for secrets and PII.
- **Reviewer Roles**: Each request specifies a required reviewer role (`admin_read`, `admin_write`, `super_admin`).
- **Audit Logs**: Every decision (Approve/Reject) is logged with the user's identity and rationale.

## Configuration

Manage escalation rules and timeout thresholds in the **Escalation Rules** settings page.
