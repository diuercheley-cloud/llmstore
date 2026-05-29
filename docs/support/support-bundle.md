---
owner: platform-ops
status: consolidated
---

# Support Bundle

The Support Bundle is a diagnostic tool designed to help the support team troubleshoot issues with your LLM Inference Stack installation without exposing sensitive data.

## Goal

Provide a comprehensive "snapshot" of the system state, including:
- Version and Git commit.
- Runtime profiles and feature flags.
- Health and readiness reports.
- Aggregated metrics.
- Sanitized logs (sensitive keys and tokens are redacted).
- Hardware summary.
- Compliance status.

## Generating a Bundle

### Via CLI

Run the following script:

```bash
./scripts/generate-support-bundle.sh
```

The bundle will be saved to `artifacts/support-bundles/support-bundle-YYYYMMDD_HHMMSS.tar.gz`.

### Via API

1. **Trigger generation**:
   `POST /admin/support/bundle`
   Header: `X-Admin-Token: <your-token>`

2. **Download latest**:
   `GET /admin/support/bundle/latest`
   Header: `X-Admin-Token: <your-token>`

## Security and Privacy

The Support Bundle explicitly **EXCLUDES**:
- User prompts and completions.
- RAG documents and data.
- API keys and tokens.
- Private keys and PKI data.
- Real `.env` files.
- Uploaded files and model binaries.

All log files and reports are processed through a redaction engine that replaces sensitive patterns (like `sk-...`) with `[REDACTED]`.

## Content of the Bundle

- `version.json`: System version, git commit, and environment mode (Docker/K8s).
- `runtime.json`: Active runtime profile and sanitized feature flags.
- `health.txt`: Output of system health checks.
- `readiness_report.json`: Latest production readiness report.
- `alembic.txt`: Database migration status.
- `api_surface.txt`: Summary of the registered API endpoints.
- `script_manifest.txt`: Summary of the script manifest validation.
- `hardware.txt`: CPU, Memory, and GPU (if available) information.
- `logs/`: Redacted logs from the control plane, data plane, and workers.
- `compliance.json`: Summary of compliance readiness.
