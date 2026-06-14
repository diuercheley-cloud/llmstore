# Secrets Management Guide

This document explains how to manage sensitive tokens and credentials in the LLM Inference Stack.

## Plain-text vs File-based Secrets

While the stack supports environment variables for configuration (e.g., `ADMIN_TOKEN`), it is recommended to use **file-based secrets** in production environments to avoid leaking credentials in process listings or logs.

### Variable Suffix `_FILE`

All sensitive variables (like `ADMIN_TOKEN`, `JWT_SECRET`, and provider API keys) support a `_FILE` suffix. When a `_FILE` variant is provided, the stack will read the secret value from the specified file path.

Example in `.env`:
```bash
ADMIN_TOKEN_FILE=/run/secrets/admin_token
```

## Docker Secrets

If you are using Docker Swarm or a compatible runtime, you can use Docker Secrets:

1. Define the secret in your `docker-compose.yml`:
   ```yaml
   services:
     control-plane:
       secrets:
         - admin_token
       environment:
         ADMIN_TOKEN_FILE: /run/secrets/admin_token

   secrets:
     admin_token:
       external: true
   ```

## Kubernetes Secrets

In Kubernetes, you can mount a Secret as a volume:

1. Create the secret:
   ```bash
   kubectl create secret generic admin-token --from-literal=token=your-secure-token
   ```

2. Mount it in your Deployment:
   ```yaml
   spec:
     containers:
     - name: control-plane
       volumeMounts:
       - name: secret-volume
         mountPath: "/etc/secrets"
         readOnly: true
       env:
       - name: ADMIN_TOKEN_FILE
         value: "/etc/secrets/token"
     volumes:
     - name: secret-volume
       secret:
         secretName: admin-token
   ```

## Production Hardening

In production environments (`APP_ENV=production`), the stack enforces the following rules:

1. **Insecure Defaults:** The stack will refuse to start if sensitive tokens are set to known insecure default values (e.g., `default-admin-token`).
2. **Minimum Length:** Sensitive tokens must be at least 32 characters long.
3. **Environment Isolation:** Secrets should never be committed to the repository. Use `.env.local` for local development and appropriate secret managers for production.

## Redaction

The stack includes a redaction engine that attempts to scrub sensitive patterns (like `ADMIN_TOKEN=...`) from logs and diagnostic support bundles. However, using file-based secrets provides the strongest protection.
