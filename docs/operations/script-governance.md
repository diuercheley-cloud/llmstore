# Operational Script Governance

This document establishes the official governance policy for operational and management scripts in the `llm-inference-stack` platform.

## Script Classifications

Every script under the `scripts/` directory is registered in `scripts/manifest.yaml` and classified into one of the following categories:

1. **`supported`**:
   - Production-ready scripts used for official administration tasks.
   - Must have a designated `owner` and `docs_url`.
   - Examples: `./scripts/up.sh`, `./scripts/down.sh`.
   
2. **`deprecated`**:
   - Outdated scripts scheduled for archive or removal. Replacement pointers are provided where available.

3. **`internal`**:
   - Helper scripts, CI/CD validation tasks, and utility automation.
   - Example: test runner execution files.

4. **`experimental`**:
   - Unstable research or trial scripts. Experimental scripts must NOT be referenced as primary recommended setup paths in the main `README.md`.

---

## Safety and Environmental Requirements

Manifest attributes determine safety rules:
- **`is_destructive`**: If `true`, the script must check for explicit user confirmation (e.g., interactive prompt `read -p` or environment flag confirmation) unless running in an automated testing environment.
- **`writes_files`**: Must declare the `outputs` paths to trace log or artifact generation.
- **`requires_network`**: Informs operators if the script accesses internet/remote repositories.
