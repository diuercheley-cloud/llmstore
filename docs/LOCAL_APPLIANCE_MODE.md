# LOCAL_APPLIANCE_MODE

`LOCAL_APPLIANCE_MODE` is a specialized operational profile for the LLM Inference Stack, designed for secure, self-contained local operation (Local Appliance).

When enabled (`LOCAL_APPLIANCE_MODE=true`), the system enforces several security and operational constraints to ensure a "secure by default" local experience.

## Enforced Settings

When `LOCAL_APPLIANCE_MODE=true` is set in `.env.local`:

1.  **LOCALHOST_MODE=true**: API endpoints default to localhost.
2.  **LOCAL_BILLING_MODE=manual**: Real payment provider integrations (PSP/PIX) are disabled in favor of manual/local billing.
3.  **PUBLIC_EXPOSURE=false**: Restricts features that might expose the system to the public internet.
4.  **PUBLIC_SIGNUP_ENABLED=false**: Disables public user registration.
5.  **CORS Restrictions**: CORS is strictly limited to localhost and standard local loopback addresses. `*` is not allowed. Secure defaults are applied automatically based on `HOST_PORT` and `PUBLIC_BASE_URL`.

## CORS Configuration

In `LOCAL_APPLIANCE_MODE`, CORS is configured to be "secure-by-default":

- **Explicit Origins**: Use `CORS_ALLOW_ORIGINS` in `.env.local` to list permitted origins (e.g., `http://localhost:3000`).
- **Secure Defaults**: If `CORS_ALLOW_ORIGINS` is empty, the system automatically allows `http://localhost`, `http://127.0.0.1`, and variants with the configured `HOST_PORT`.
- **Wildcard Forbidden**: Setting `CORS_ALLOW_ORIGINS=*` is strictly forbidden in appliance mode and will be ignored (falling back to secure defaults).
- **Validation**: Use `./scripts/validate-cors-local-appliance.sh` to verify your CORS setup.

## Security Guards

The appliance mode introduces several guards, especially during the release process:

-   **Admin Token Validation**: The system issues warnings if a default or weak `ADMIN_TOKEN` is detected.
-   **Secrets Scanning**: `scripts/release-local-production.sh` enforces a full secrets scan using `scripts/check-secrets.sh` before allowing a release.
-   **Data Protection**: Local data directories like `models/` and `data/rag_uploads/` are strictly excluded from release bundles created via `scripts/create-release-bundle.sh`.
-   **Production Readiness**: Releases require (or strongly recommend) a `production-readiness-local.sh` check.

## How to Enable

The easiest way to enable and configure `LOCAL_APPLIANCE_MODE` is by using the **Configuration Wizard**:

```bash
make configure-local
```

This wizard will guide you through the setup of `.env.local` and ensure all appliance-specific settings are correctly applied.

Alternatively, you can enable it manually by adding or updating the following in your `.env.local`:


```env
LOCAL_APPLIANCE_MODE=true
```

## Validation

You can validate your appliance mode configuration using the provided script:

```bash
./scripts/validate-local-appliance-mode.sh
```

This script verifies that the mode is active, billing is manual, CORS is restricted, and all security guards are in place.
