# New Maintainer Onboarding Checklist

Welcome to the LLM Inference Stack maintainer team! This checklist will guide you through your first steps.

## Phase 1: Access & Environment
- [ ] Get invited to the GitHub/GitLab organization.
- [ ] Set up SSH keys for repository access.
- [ ] Clone the repository and follow `MAINTAINER_RUNBOOK.md` for local setup.
- [ ] Verify `make validate-all` passes on your machine.

## Phase 2: Understanding the Stack
- [ ] Read `README.md` and `docs/OWNERSHIP.md`.
- [ ] Explore `control_plane/app/services/` to understand business logic.
- [ ] Familiarize yourself with the agent runtime in `control_plane/app/services/agents/`.
- [ ] Review the security scanning process in `scripts/validators/validate_security_scan.py`.

## Phase 3: First Contributions
- [ ] Fix a "good first issue" or small bug.
- [ ] Create a PR and ensure all CI checks (including security) pass.
- [ ] Pair with an existing maintainer on a release following the runbook.

## Phase 4: Operational Readiness
- [ ] Perform a successful local backup and restore.
- [ ] Walk through the rollback procedure in dry-run mode.
- [ ] Join the internal incident response communication channel.
