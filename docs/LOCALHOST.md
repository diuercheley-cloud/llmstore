# Localhost Mode

This document explains how to run the LLM Inference Stack in a standardized local environment using `http://localhost`.

## Prerequisites

- Docker and Docker Compose
- NVIDIA Container Toolkit (for GPU support, optional but recommended)
- WSL2 (if on Windows)

## Quick Start

1. **Prepare Environment:**
   Copy the example environment file:
   ```bash
   cp .env.example .env.local
   ```
   Ensure `LOCALHOST_MODE=true` is set in your `.env.local`.

2. **Start the Stack:**
   ```bash
   STACK_ENV_FILE=.env.local docker compose up -d
   ```

3. **Validate the Setup:**
   Run the validation script:
   ```bash
   ./scripts/validate-localhost-mode.sh
   ```

## Services URLs (Localhost Mode)

When `LOCALHOST_MODE=true` is enabled, the following default URLs are used:

| Service | URL |
|---------|-----|
| Control Plane API | http://localhost:18080 |
| Admin Dashboard | http://localhost:18080/admin |
| Client Portal | http://localhost:18080/client-portal |
| Documentation | http://localhost:18080/docs |
| OpenAI Compatible API | http://localhost:18080/v1 |

## CORS Support

In Localhost Mode, the Control Plane automatically allows requests from:
- `http://localhost`
- `http://localhost:18080`
- `http://localhost:3000` (Common UI dev port)
- `http://localhost:3001` (Common UI dev port)
- `http://127.0.0.1`

## Customization

You can still override any of the base URLs in your `.env.local` file if you need to use different ports or paths.

```env
PUBLIC_BASE_URL=http://localhost:8080
API_BASE_URL=http://localhost:8080/api/v1
```

## Troubleshooting

- **Port Conflicts:** If port 18080 is already in use, change `HOST_PORT` in your `.env.local`.
- **CORS Errors:** Ensure your frontend origin is listed in `CORS_ALLOW_ORIGINS` or matches one of the defaults in Localhost Mode.
- **GPU Issues:** Check `docker compose logs data-plane-gemma` to ensure the model is loading correctly on the GPU.
