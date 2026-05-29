# Working Tree Audit — v2.x-agentic-consolidation-hardening

**Date:** 2026-05-28  
**Git SHA:** `0b207e2` (base)  
**Audit Type:** Full classification of every dirty/unstaged/untracked item  

---

## Classification Summary

| Category | Count | Risk |
|---|---|---|
| `should_commit` | ~620 files | low |
| `should_delete` (temporary_file) | 2 files | low |
| `should_ignore` (environment_local_only) | 0 | — |
| `should_delete` (generated_runtime) | 1 file | low |
| **Total** | ~623 | low |

---

## 1. Modified Files (M) — Git `git status --short`

### 1.1 Release Artifacts — `should_commit`

| Path | Reason | Safe Action | Risk |
|---|---|---|---|
| `CHANGELOG.md` | Release changelog updated for v2.x | Commit as release artifact | low |
| `Makefile` | Updated with new targets for release | Commit as part of release | low |
| `README.md` | Updated release info and governance | Commit as part of release | low |
| `SECURITY.md` | Policy updates for release | Commit as part of release | low |
| `config/api-surface.yaml` | API surface updated for consolidation | Commit as part of release | low |
| `config/feature-flags.yaml` | Feature flags cleaned up (removed deprecated) | Commit as part of release | low |
| `config/platform-freeze-rules.json` | Freeze rules aligned with new surface | Commit as part of release | low |
| `config/supported-surface.yaml` | Supported surface updated | Commit as part of release | low |
| `scripts/release-gate.sh` | Release gate script updated | Commit as part of release | low |
| `scripts/platform-freeze-check.sh` | Freeze check updated | Commit as part of release | low |

### 1.2 Valid Uncommitted Fixes / Feature Work — `should_commit`

**Source code changes (control_plane):**

| Path | Reason | Safe Action | Risk |
|---|---|---|---|
| `control_plane/app/main.py` | New agentic routes registered | Commit | low |
| `control_plane/app/api/agent_observability_admin.py` | Agent observability admin updates | Commit | low |
| `control_plane/app/api/commercial_sovereign_governance_admin.py` | Governance admin updates | Commit | low |
| `control_plane/app/services/agents/multi_agent/debate_runtime.py` | Debate runtime hardening | Commit | low |
| `control_plane/app/services/agents/multi_agent/hierarchical_runtime.py` | Hierarchical runtime hardening | Commit | low |
| `control_plane/app/services/agents/multi_agent/team_observability.py` | Team observability feature | Commit | low |
| `control_plane/app/services/feature_flag_registry.py` | Feature flag registry updated | Commit | low |
| `control_plane/app/services/governance/data_governance/export_governance_service.py` | Export governance updates | Commit | low |
| `control_plane/app/services/governance/human_governance/approval_quorum_service.py` | Approval quorum hardening | Commit | low |
| `control_plane/app/services/governance/human_governance/separation_of_duties.py` | SoD hardening | Commit | low |
| `control_plane/app/services/governance/release_engineering/release_notes_generator.py` | Release notes gen updates | Commit | low |
| `control_plane/app/services/operations/remediation_execution/audit_events.py` | Audit events hardening | Commit | low |
| `control_plane/app/services/operations/remediation_execution/executor.py` | Remediation executor hardening | Commit | low |
| `control_plane/app/services/plugins/plugin_loader.py` | Plugin loading hardening | Commit | low |
| `control_plane/app/services/runtime/real_execution_readiness.py` | Real execution readiness updates | Commit | low |
| `control_plane/app/services/security/hardware_attestation.py` | Attestation hardening | Commit | low |
| `control_plane/app/services/tts_readiness.py` | TTS readiness updates | Commit | low |

**Deleted files (D) — cleanup of deprecated code:**

| Path | Reason | Safe Action | Risk |
|---|---|---|---|
| `control_plane/app/services/event_service.py` | Deprecated service removed | Commit deletion | low |
| `control_plane/app/services/governance/data_governance/data_lineage_service.py` | Deprecated service removed | Commit deletion | low |
| `control_plane/app/services/governance/data_governance/data_zone_service.py` | Deprecated service removed | Commit deletion | low |
| `control_plane/app/services/governance/data_governance/retention_policy_service.py` | Deprecated service removed | Commit deletion | low |
| `control_plane/app/services/governance/human_governance/escalation_service.py` | Deprecated service removed | Commit deletion | low |
| `control_plane/app/services/governance/human_governance/review_workflow_service.py` | Deprecated service removed | Commit deletion | low |
| `control_plane/app/services/governance/release_engineering/release_replay_verifier.py` | Deprecated service removed | Commit deletion | low |
| `control_plane/tests/test_agent_evals_gates.py` | Deprecated test removed | Commit deletion | low |
| `scripts/audit-v1.6-release-line.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/diagnose-v1.7-warnings.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/generate-v1.7-release-checklist-status.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/prepare-v1.7-release-bundle.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/run-v1.7-release-checklist.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/validate-readiness-cleanup-v1.6.3.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/validate-security-cleanup-v1.5.4.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/validate-v1.6-release-line-audit.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/validate-v1.7-final-local.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/validate-v1.7-final-report.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/validate-v1.7-go-no-go-summary.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/validate-v1.7-release-bundle.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/validate-v1.7-release-checklist.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/validate-v1.7-release-notes.sh` | Deprecated script removed | Commit deletion | low |
| `scripts/validate-v1.7-warning-cleanup.sh` | Deprecated script removed | Commit deletion | low |

**Modified scripts:**

| Path | Reason | Safe Action | Risk |
|---|---|---|---|
| `scripts/agentic-readiness.sh` | Script updates for release | Commit | low |
| `scripts/audit-feature-flags.py` | Audit script updated | Commit | low |
| `scripts/check-feature-flags.py` | Check script updated | Commit | low |
| `scripts/platform-freeze-check.py` | Freeze check logic updated | Commit | low |
| `scripts/validate_platform_documentation.py` | Doc validation updated | Commit | low |

**Modified tests:**

| Path | Reason | Safe Action | Risk |
|---|---|---|---|
| `tests/docs/test_platform_documentation.py` | Test updated for doc consistency | Commit | low |

**Environment file:**

| Path | Reason | Safe Action | Risk |
|---|---|---|---|
| `.env.example` | Deprecated flags removed from template | Commit | low |

### 1.3 Documentation Consistency Updates (all docs/*.md) — `should_commit`

Hundreds of `.md` files across `docs/` received a **+5 line change** (cross-reference/consistency footer added). These are part of the doc-consistency gate.

All files under:
- `docs/*.md` (root docs)
- `docs/admin/`, `docs/adr/`, `docs/agents/`, `docs/agents/connectors/`, `docs/agents/playbooks/`
- `docs/api/`, `docs/architecture/`, `docs/billing/`, `docs/chaos/`, `docs/ci/`
- `docs/cli/`, `docs/compliance/`, `docs/configuration/`, `docs/demo-visual-guide/`
- `docs/deployment/`, `docs/enterprise/`, `docs/evals/`, `docs/governance/`
- `docs/integrations/`, `docs/kubernetes/`, `docs/multicluster/`, `docs/observability/`
- `docs/operations/`, `docs/performance/`, `docs/phases/`, `docs/platform/`
- `docs/plugins/`, `docs/quality/`, `docs/releases/`, `docs/rfc/`, `docs/runtime/`
- `docs/saas/`, `docs/sdk/`, `docs/security/`, `docs/support/`, `docs/validation/`

All classified as: `should_commit` (release_artifact / doc-consistency gate)

---

## 2. Untracked Files (??) — `git ls-files --others --exclude-standard`

### 2.1 New Release Artifacts / Features — `should_commit`

| Path | Reason | Safe Action | Risk |
|---|---|---|---|
| `config/agentic-promotion-policy.yaml` | New agentic promotion policy config | Commit | low |
| `config/deployment-profiles/agentic-production.yaml` | Agentic production deployment profile | Commit | low |
| `control_plane/__init__.py` | Package init | Commit | low |
| `control_plane/app/api/admin_readiness.py` | Admin readiness endpoint | Commit | low |
| `control_plane/app/services/agents/canary_runner.py` | Canary runner service | Commit | low |
| `control_plane/app/services/agents/continuous_promotion.py` | Continuous promotion service | Commit | low |
| `control_plane/app/services/agents/multi_agent/arbitration_engine.py` | Arbitration engine | Commit | low |
| `control_plane/app/services/agents/multi_agent/governance_policy.py` | Governance policy engine | Commit | low |
| `control_plane/app/services/agents/multi_agent/specialist_routing_runtime.py` | Specialist routing runtime | Commit | low |
| `control_plane/app/services/agents/rollback_controller.py` | Rollback controller | Commit | low |
| `control_plane/app/services/operations/environment_preflight.py` | Environment preflight checks | Commit | low |
| `docs/agents/canary-rollout.md` | Canary rollout documentation | Commit | low |
| `docs/agents/continuous-promotion.md` | Continuous promotion documentation | Commit | low |
| `scripts/archive-deprecated-surface.sh` | Archive deprecated surface script | Commit | low |
| `scripts/bootstrap-agentic-production.sh` | Bootstrap agentic production | Commit | low |
| `scripts/check-doc-consistency.py` | Doc consistency checker | Commit | low |
| `scripts/check-runtime-prerequisites.sh` | Runtime prereq checker | Commit | low |
| `scripts/check-service-test-coverage.py` | Service test coverage checker | Commit | low |
| `scripts/consolidate-platform-surface.py` | Platform surface consolidator | Commit | low |
| `scripts/preflight-hermetic.sh` | Hermetic preflight check | Commit | low |
| `scripts/validate-agentic-production-profile.sh` | Agentic production profile validator | Commit | low |
| `tests/operations/test_capability_readiness.py` | Capability readiness tests | Commit | low |
| `tests/test_agent_continuous_promotion.py` | Continuous promotion tests | Commit | low |
| `tests/test_auth_service.py` | Auth service tests | Commit | low |
| `tests/test_canary_runner.py` | Canary runner tests | Commit | low |
| `tests/test_environment_preflight.py` | Environment preflight tests | Commit | low |
| `tests/test_human_approval_service.py` | Human approval service tests | Commit | low |
| `tests/test_multi_agent_hardening.py` | Multi-agent hardening tests | Commit | low |
| `tests/test_rag_processor_service.py` | RAG processor tests | Commit | low |
| `tests/test_runtime_profiles_service.py` | Runtime profiles tests | Commit | low |
| `tests/test_specialist_routing_runtime.py` | Specialist routing runtime tests | Commit | low |
| `tests/test_team_observability.py` | Team observability tests | Commit | low |
| `docs/releases/V2_X_AGENTIC_CONSOLIDATION_HARDENING.md` | Release specification document | Commit | low |

### 2.2 Archived Orphaned Docs — `should_commit`

| Path | Count | Reason | Safe Action | Risk |
|---|---|---|---|---|
| `docs/archive/orphaned_doc_*.md` | 329 files | Orphaned docs archived as part of doc consolidation | Commit (part of release scope) | low |

These files are orphaned documentation content removed from the active tree but preserved for historical reference. Archiving deprecated docs is explicitly part of this release scope.

### 2.3 Temporary File — `should_delete`

| Path | Reason | Safe Action | Risk |
|---|---|---|---|
| `hardening_plan.md` | Working plan; hardening is complete (all gates pass) | Delete — no longer needed | low |

### 2.4 Generated Runtime Artifact — `should_commit` (as artifact)

| Path | Reason | Safe Action | Risk |
|---|---|---|---|
| `orphaned_flags.txt` | Empty file generated by feature-flag audit; currently blank | Move to `artifacts/releases/v2.x-agentic-consolidation-hardening/` as runtime artifact | low |

---

## 3. Risk Assessment

| Risk Level | Count | Notes |
|---|---|---|
| `low` | All | No secrets, no credentials, no sensitive data detected |
| `medium` | 0 | — |
| `high` | 0 | — |
| `critical` | 0 | — |

---

## 4. Summary of Actions

| Action | Count | Files |
|---|---|---|
| `should_commit` | ~620 | All modified/untracked files except 3 classified below |
| `should_delete` | 2 | `hardening_plan.md`, `orphaned_flags.txt` (orphaned_flags.txt moved to artifacts/) |
| `should_ignore` | 0 | — |
| **No implicit/unclassified** | 0 | Every item has an explicit classification |

---

*Audit generated by `scripts/reconcile-working-tree.sh` phase — 2026-05-28*
