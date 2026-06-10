# Frontend & SDK Unified Workspace

## Overview
This repository uses `npm` workspaces to manage frontend applications (`frontend/admin`, `frontend/client`) and the Node.js SDK (`sdk/node`).

## Workspace Structure
- Root: `package.json` manages workspace-wide scripts.
- `frontend/admin`: Admin dashboard application.
- `frontend/client`: Client-facing application.
- `sdk/node`: Node.js SDK.

## Standardized Scripts
From the root directory, you can run commands across all workspaces:
- `npm run build`: Builds all workspaces.
- `npm run lint`: Lints all workspaces.
- `npm run test`: Tests all workspaces.
- `npm run typecheck`: Runs TypeScript checks for all workspaces.

## Release Policy
- Publication of packages (especially SDK) and deployment of frontends must ONLY occur through the designated CI/CD pipeline.
- Versioning follows semantic versioning (SemVer).

## OpenAPI & SDK Generation
- Where applicable, SDKs should be generated from OpenAPI contracts using the designated build pipeline.
EOF
