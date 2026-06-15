# Frontend Build and Artifact Management Workflow

This document details the architecture, build processes, CI pipeline configurations, and Docker integration for the frontend assets in the LLM Inference Stack.

## Overview

To prevent bloated repositories and ensure reproducible builds, all compiled frontend assets are excluded from version control. 

### Static vs. Compiled Assets
*   **Static Sources (Tracked)**: Legacy frontend assets such as `control_plane/app/static/www/`, `control_plane/app/static/portal/`, and `control_plane/app/static/shared/` contain handwritten legacy code. These remain versioned in git.
*   **Compiled Assets (Untracked)**: The modern React/Vite admin dashboard in [frontend/admin](file:///home/kleber/llm-inference-stack/frontend/admin) and client portal in [frontend/client](file:///home/kleber/llm-inference-stack/frontend/client) generate compiled production builds that are excluded from git.
    *   `frontend/admin` builds to [control_plane/app/static/admin-v2](file:///home/kleber/llm-inference-stack/control_plane/app/static/admin-v2)
    *   `frontend/client` builds to `frontend/client/dist/`

---

## Local Development Workflow

To compile the frontend projects locally, you can use the root `npm` workspaces commands.

### Prerequisites
*   Node.js (v20 or higher)
*   npm (v10 or higher)

### Build Commands
Run the build script from the repository root:
```bash
# Build all workspaces (admin frontend, client frontend, and node SDK)
npm run build
```

This will automatically trigger:
1.  Vite build for `frontend/admin` (outputs directly to `control_plane/app/static/admin-v2`).
2.  Vite build for `frontend/client` (outputs to `frontend/client/dist/`).

---

## Docker Integration

To support both clean host environments (where developers haven't run `npm run build`) and pipeline runners, Docker images use **multi-stage builds** to build the frontend inside the container.

The following Dockerfiles implement this pattern:
*   [docker/control-plane/Dockerfile](file:///home/kleber/llm-inference-stack/docker/control-plane/Dockerfile)
*   [Dockerfile.quickstart](file:///home/kleber/llm-inference-stack/Dockerfile.quickstart)

### Multi-Stage Build Details
```dockerfile
# Stage 0: Build frontend static assets
FROM node:20-slim AS frontend-builder
WORKDIR /app
COPY package.json package-lock.json ./
COPY frontend/admin/package.json ./frontend/admin/
COPY frontend/client/package.json ./frontend/client/
COPY sdk/node/package.json ./sdk/node/
RUN npm ci
COPY frontend/admin ./frontend/admin
RUN npm run build --workspace=frontend/admin

# Stage 2: Final runtime image
FROM python:3.12-slim
...
COPY control_plane /app/control_plane
COPY --from=frontend-builder /app/control_plane/app/static/admin-v2 /app/control_plane/app/static/admin-v2
```

---

## CI/CD Pipeline Artifacts

### GitLab CI
The frontend test stage in [.gitlab/ci/frontend.yml](file:///home/kleber/llm-inference-stack/.gitlab/ci/frontend.yml) compiles the frontends and saves the production builds as pipeline artifacts:
```yaml
artifacts:
  paths:
    - control_plane/app/static/admin-v2/
    - frontend/client/dist/
```
These artifacts are automatically inherited by downstream jobs (such as `docker:build` in [.gitlab/ci/docker.yml](file:///home/kleber/llm-inference-stack/.gitlab/ci/docker.yml)).

### GitHub Actions
The CI workflow [.github/workflows/ci.yml](file:///home/kleber/llm-inference-stack/.github/workflows/ci.yml) uploads the builds:
*   `frontend-admin-artifacts`: Contains `control_plane/app/static/admin-v2/`
*   `frontend-client-artifacts`: Contains `frontend/client/dist/`

### Release Attachments
When a tag is pushed, [.github/workflows/release.yml](file:///home/kleber/llm-inference-stack/.github/workflows/release.yml) compiles the frontends, packages them as zip files, and attaches them directly to the GitHub Release:
*   `admin-v2-build.zip`
*   `client-build.zip`
