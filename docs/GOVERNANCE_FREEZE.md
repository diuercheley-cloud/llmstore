# Architectural Surface Freeze Policy

## Context
To ensure platform stability and prevent technical debt, we are enforcing a temporary freeze on the expansion of the architectural surface.

## Scope of Freeze
The following additions are strictly prohibited without an explicit, approved exception:
- **New API Routers**: No new routers in `control_plane/app/api`.
- **New Feature Flags**: No new flags in `config/feature-flags.yaml`.
- **New Service Models**: No new files in `control_plane/app/services`.
- **New Workflows**: No new files in `.github/workflows`.
- **New Migrations**: No new database migration files.

## Approved Exceptions
Exceptions must be documented in `governance/approved_surface_exceptions.yml` and signed off by the architecture review board.

## Approval Process
1. Raise a PR to add an entry to `governance/approved_surface_exceptions.yml`.
2. Include justification, architectural impact, and duration of the exception.
3. Obtain approval from designated maintainers.
4. Merge the PR.

## Duration
This policy is in effect until current budget metrics are back within defined limits.
