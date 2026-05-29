# Meta-Reviewer

## Overview
The Meta-Reviewer is a real-time validation layer designed to intercept agent outputs and high-risk actions before they reach the user or affect the system. It acts as an "internal auditor" that ensures every step is factually consistent, ethically safe, and aligned with organizational policies.

## Key Capabilities
- **Real-time Auditing**: Runs in parallel or sequential mode before final delivery.
- **Fact-Checking**: Compares candidate responses against retrieved evidence (tool outputs, memory blocks).
- **Ethical Guardrails**: Detects unsafe content, malicious intent, or potential bias.
- **Policy Enforcement**: Ensures that high-risk actions (e.g., data deletion) have explicit human approval in context.

## Operational Modes
1. **Advisory Mode (`BLOCKING_MODE=false`)**: Reviewer generates findings and decisions, but does not prevent delivery. Used for observability and data collection.
2. **Blocking Mode (`BLOCKING_MODE=true`)**: If the reviewer returns a `block` or `require_human_approval` decision, the agent runtime intercepts the delivery and returns a safety error or escalates to HITL.

## Configuration
Enable the reviewer via `AGENT_META_REVIEWER_ENABLED=true`.
Monitor decisions and findings via the administrative APIs.
