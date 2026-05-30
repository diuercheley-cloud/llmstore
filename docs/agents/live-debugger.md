# Live Agentic Debugger

The Live Agentic Debugger provides interactive control over agent execution, allowing developers to pause runs, inspect state, and step through the reasoning process.

## Features

- **Breakpoints**: Automatically pause execution based on specific triggers:
  - `step_start`: Before any reasoning step.
  - `tool_name`: When a specific tool is about to be called.
  - `policy_denial`: When a guardrail blocks an action.
  - `approval_request`: When human-in-the-loop is triggered.
  - `error`: When an unhandled exception occurs.
- **Live Stepping**: Manually control each step of the agent's reasoning.
- **State Inspection**: View snapshots of the agent's internal state, memory references, and policy decisions.
- **Security**:
  - **Secrets Redaction**: Automatic scrubbing of API keys and passwords from snapshots.
  - **CoT Sanitization**: Redaction of internal Chain-of-Thought reasoning for production privacy.

## Configuration

Enable the debugger via environment variables:

```bash
AGENT_DEBUGGER_ENABLED=true
AGENT_LIVE_STEPPING_ENABLED=true
AGENT_BREAKPOINTS_ENABLED=true
```

## Using the Debugger API

### 1. Set a Breakpoint
Pause execution whenever the `search_web` tool is called.

```bash
POST /api/v1/admin/debugger/breakpoints/{run_id}?type=tool_name&target=search_web
```

### 2. Inspect Current State
Get the latest state snapshot and step information.

```bash
GET /api/v1/admin/debugger/sessions/{run_id}/state
```

### 3. Resume Execution
Continue running until the next breakpoint or completion.

```bash
POST /api/v1/admin/debugger/sessions/{run_id}/resume
```

## Security and RBAC

The debugger is an administrative tool. Access requires:
- `admin_read` or `admin_write` scopes.
- Membership in the same tenant as the agent run.
- Explicit `AGENT_DEBUGGER_ENABLED` flag on the platform.
