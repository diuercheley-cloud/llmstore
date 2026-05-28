# Agent Code Interpreter

The enterprise code interpreter is safe-by-default.

- `AGENT_CODE_INTERPRETER_ENABLED=false` keeps the feature disabled.
- `AGENT_CODE_SANDBOX_PROVIDER=mock` avoids executing dynamic code by default.
- Real execution requires an explicit provider enablement such as `docker`.
- Network and write access remain disabled unless separately enabled.

Security guarantees:

- No production path relies on Python `exec()` for real execution.
- All code is validated by the sandbox policy before provider dispatch.
- Protected paths such as `.env` and `/etc/passwd` are blocked.
- Artifact contents are scanned for secret-like material before persistence.
