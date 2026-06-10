# Runtime Security Policy

## Docker Socket Access
- The `docker.sock` mount is **prohibited** in default production and local staging environments.
- If required for specific development or sandbox scenarios, the `docker-compose.dev.yml` override MUST be used explicitly: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`.

## Secret Management
- All critical secrets (`JWT_SECRET`, API keys, encryption keys) **must** be set to unique, secure values.
- The system will **fail to start** if `JWT_SECRET` is left as the default placeholder or is too short.

## Capabilities and Mounts
- GPU and utility capabilities are restricted via Docker Compose `deploy` configurations.
- Host volume mounts should be minimized, read-only where possible (e.g., `:ro` for configs).
