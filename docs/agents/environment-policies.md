# Environment Policies

## Overview
Environment policies define safety and operational constraints based on where an agent is running (`dev`, `staging`, `production`, `sovereign`, etc.).

## Default Rules
- **`production`**: Requires a valid evaluation baseline and human approval for activation.
- **`sovereign`**: Blocks all external tool calls (APIs outside the sovereign boundary) by default.
- **`managed`**: Enforces strict resource quotas and cost limits.

## Destructive Tools
Tools with side effects (e.g., `delete`, `write`) require elevated privileges (`agent_security_admin`) or a specific policy exception in restricted environments.

## Exceptions
Policy exceptions can be granted for specific agents. Exceptions have a mandatory reason, an approver, and an expiration date.
