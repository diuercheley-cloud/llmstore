# Red-Team Evaluations

Adversarial testing is critical for ensuring agent safety and security. Our red-teaming framework automates common attack vectors.

## Attack Categories

### 1. Jailbreaking
Attempts to bypass the agent's system prompt or safety guardrails using complex scenarios (e.g., "DAN" style attacks).

### 2. Prompt Injection
Inserting malicious instructions into user inputs to hijack the agent's execution flow.

### 3. Data Exfiltration
Prompting the agent to reveal sensitive information, such as API keys, secrets, or internal system details.

### 4. Unsafe Tool Use
Tricking the agent into calling sensitive tools with malicious parameters or in unauthorized contexts.

## Automated Scanning

The `RedTeamScanner` uses a combination of heuristic patterns and model-based detection to identify successful attacks.

## Red-Team Suites

Teams can define custom red-team suites tailored to their specific agentic domains. These suites are run during the evaluation phase, and any failure blocks the promotion gate.
