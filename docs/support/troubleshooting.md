# Troubleshooting Guide

This guide provides steps to diagnose and resolve common issues with the LLM Inference Stack.

## 1. Initial Diagnosis

Always start by generating a **Support Bundle**. This will give you a comprehensive overview of the system state without exposing sensitive data.

```bash
./scripts/generate-support-bundle.sh
```

Review the `health.txt` and `readiness_report.json` inside the bundle.

## 2. Common Issues

### API Errors (500, 401, 403)
- Check `logs/control-plane.log` for stack traces.
- Verify `ADMIN_TOKEN` and `API_KEY` are correctly configured.
- Ensure the database is reachable and migrations are up to date (`alembic.txt`).

### Model Execution Failures
- Check `logs/data-plane.log`.
- Verify GPU availability in `hardware.txt`.
- Check if the model is correctly registered and active in `api_surface.txt`.

### Connectivity Issues
- Verify if you are running in Docker or K8s mode (`version.json`).
- Check network aliases and ports in your `.env` file (sanitized version can be inferred from `runtime.json`).

## 3. Seeking Support

If you cannot resolve the issue yourself, please share the latest **Support Bundle** with the support team.

**Important:** Do NOT send your `.env` file or any `data/pki` contents. The Support Bundle is already sanitized and safe to share.

## 4. Maintenance Commands

- **Check Health**: `./scripts/test-health.sh`
- **Full Validation**: `./scripts/validate-e2e.sh`
- **Clear Cache**: `./scripts/cache-clear.sh`
