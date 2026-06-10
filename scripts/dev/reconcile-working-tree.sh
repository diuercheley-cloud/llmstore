#!/bin/bash
# reconcile-working-tree.sh
# Reconcilia o working tree para release — classifica, organiza e prepara staging.
# NÃO executa commit, apenas prepara o estado reconciliado.
set -euo pipefail

RELEASE_TAG="${1:-v2.x-agentic-consolidation-hardening}"
ARTIFACT_DIR="artifacts/releases/$RELEASE_TAG"
RUNTIME_DIR="artifacts/runtime"
mkdir -p "$ARTIFACT_DIR" "$RUNTIME_DIR"

echo "=========================================="
echo "  Working Tree Reconciliation"
echo "  Release: $RELEASE_TAG"
echo "=========================================="
echo ""

# ------------------------------------------------------------------
# CLASSIFICATION (from working-tree-audit.md)
# ------------------------------------------------------------------
echo "--- Step 1: Classifying all changes ---"

# 1.1 Release artifacts — stage for commit (source code, config, docs)
echo "[1.1] Staging release artifacts (source, config, docs)..."

git add \
  Makefile \
  README.md \
  SECURITY.md \
  CHANGELOG.md \
  .env.example \
  config/api-surface.yaml \
  config/feature-flags.yaml \
  config/platform-freeze-rules.json \
  config/supported-surface.yaml \
  config/agentic-promotion-policy.yaml \
  config/deployment-profiles/agentic-production.yaml \
  "$ARTIFACT_DIR/working-tree-audit.md" \
  2>/dev/null || echo "  (some files already staged or missing)"

git add \
  control_plane/__init__.py \
  control_plane/app/main.py \
  control_plane/app/api/admin_readiness.py \
  control_plane/app/api/agent_observability_admin.py \
  control_plane/app/api/commercial_sovereign_governance_admin.py \
  control_plane/app/services/agents/canary_runner.py \
  control_plane/app/services/agents/continuous_promotion.py \
  control_plane/app/services/agents/rollback_controller.py \
  control_plane/app/services/agents/multi_agent/arbitration_engine.py \
  control_plane/app/services/agents/multi_agent/debate_runtime.py \
  control_plane/app/services/agents/multi_agent/governance_policy.py \
  control_plane/app/services/agents/multi_agent/hierarchical_runtime.py \
  control_plane/app/services/agents/multi_agent/specialist_routing_runtime.py \
  control_plane/app/services/agents/multi_agent/team_observability.py \
  control_plane/app/services/feature_flag_registry.py \
  control_plane/app/services/governance/data_governance/export_governance_service.py \
  control_plane/app/services/governance/human_governance/approval_quorum_service.py \
  control_plane/app/services/governance/human_governance/separation_of_duties.py \
  control_plane/app/services/governance/release_engineering/release_notes_generator.py \
  control_plane/app/services/operations/environment_preflight.py \
  control_plane/app/services/operations/remediation_execution/audit_events.py \
  control_plane/app/services/operations/remediation_execution/executor.py \
  control_plane/app/services/plugins/plugin_loader.py \
  control_plane/app/services/runtime/real_execution_readiness.py \
  control_plane/app/services/security/hardware_attestation.py \
  control_plane/app/services/tts_readiness.py \
  tests/integration/operations/test_capability_readiness.py \
  tests/test_agent_continuous_promotion.py \
  tests/test_auth_service.py \
  tests/test_canary_runner.py \
  tests/test_environment_preflight.py \
  tests/test_human_approval_service.py \
  tests/test_multi_agent_hardening.py \
  tests/test_rag_processor_service.py \
  tests/test_runtime_profiles_service.py \
  tests/test_specialist_routing_runtime.py \
  tests/test_team_observability.py \
  2>/dev/null || echo "  (some files already staged or missing)"

# 1.2 Deleted files — stage deletions
echo "[1.2] Staging deleted (deprecated code)..."
git add \
  control_plane/app/services/event_service.py \
  control_plane/app/services/governance/data_governance/data_lineage_service.py \
  control_plane/app/services/governance/data_governance/data_zone_service.py \
  control_plane/app/services/governance/data_governance/retention_policy_service.py \
  control_plane/app/services/governance/human_governance/escalation_service.py \
  control_plane/app/services/governance/human_governance/review_workflow_service.py \
  control_plane/app/services/governance/release_engineering/release_replay_verifier.py \
  tests/control_plane/test_agent_evals_gates.py \
  scripts/archive/legacy/audit-v1.6-release-line.sh \
  scripts/diagnose-v1.7-warnings.sh \
  scripts/archive/legacy/generate-v1.7-release-checklist-status.sh \
  scripts/prepare-v1.7-release-bundle.sh \
  scripts/run-v1.7-release-checklist.sh \
  scripts/archive/legacy/validate-readiness-cleanup-v1.6.3.sh \
  scripts/archive/legacy/validate-security-cleanup-v1.5.4.sh \
  scripts/archive/legacy/validate-v1.6-release-line-audit.sh \
  scripts/validate-v1.7-final-local.sh \
  scripts/validate-v1.7-final-report.sh \
  scripts/validate-v1.7-go-no-go-summary.sh \
  scripts/validate-v1.7-release-bundle.sh \
  scripts/archive/legacy/validate-v1.7-release-checklist.sh \
  scripts/validate-v1.7-release-notes.sh \
  scripts/validate-v1.7-warning-cleanup.sh \
  2>/dev/null || echo "  (some already staged)"

# 1.3 Scripts updates
echo "[1.3] Staging script updates..."
git add \
  scripts/dev/agentic-readiness.sh \
  scripts/legacy/archive-deprecated-surface.sh \
  scripts/validators/audit-feature-flags.py \
  scripts/deploy/bootstrap-agentic-production.sh \
  scripts/validators/check-doc-consistency.py \
  scripts/legacy/check-feature-flags.py \
  scripts/validators/check-runtime-prerequisites.sh \
  scripts/validators/check-service-test-coverage.py \
  scripts/legacy/consolidate-platform-surface.py \
  scripts/validators/platform-freeze-check.py \
  scripts/validators/platform-freeze-check.sh \
  scripts/legacy/preflight-hermetic.sh \
  scripts/release/release-gate.sh \
  scripts/validators/validate-agentic-production-profile.sh \
  scripts/validators/validate_platform_documentation.py \
  2>/dev/null || echo "  (some already staged)"

# 1.4 Documentation — docs consistency updates + new docs
echo "[1.4] Staging documentation updates..."
git add \
  docs/agents/canary-rollout.md \
  docs/agents/continuous-promotion.md \
  docs/releases/V2_X_AGENTIC_CONSOLIDATION_HARDENING.md \
  docs/releases/working-tree-governance.md \
  tests/integration/docs/test_platform_documentation.py \
  2>/dev/null || echo "  (some already staged)"

# All the modified docs (consistency footer updates)
# Use git add with all modified docs to capture the +5 line changes
# This is safe because these are all vetted doc-consistency updates
git add docs/ 2>/dev/null || echo "  (docs may already be staged)"

# 1.5 Archive orphaned docs
echo "[1.5] Staging archived orphaned docs..."
git add docs/archive/ 2>/dev/null || echo "  (archive already staged)"

# ------------------------------------------------------------------
# HANDLE TEMPORARY AND GENERATED FILES
# ------------------------------------------------------------------
echo ""
echo "--- Step 2: Handling temporary and generated files ---"

# 2.1 hardening_plan.md — temporary, delete
if [ -f hardening_plan.md ]; then
  echo "[2.1] Removing temporary file: hardening_plan.md"
  rm -v hardening_plan.md
fi

# 2.2 orphaned_flags.txt — move to artifacts
if [ -f orphaned_flags.txt ]; then
  echo "[2.2] Moving orphaned_flags.txt to $ARTIFACT_DIR/"
  mv -v orphaned_flags.txt "$ARTIFACT_DIR/orphaned-flags-audit.txt"
fi

# ------------------------------------------------------------------
# STAGE NEW RUNTIME SCRIPTS
# ------------------------------------------------------------------
echo ""
echo "--- Step 3: Staging new governance scripts ---"
git add \
  scripts/dev/reconcile-working-tree.sh \
  scripts/validators/check-working-tree-governance.sh \
  config/working-tree-governance.yaml \
  2>/dev/null || echo "  (scripts already staged)"

# ------------------------------------------------------------------
# STAGE TESTS
# ------------------------------------------------------------------
echo "--- Step 4: Staging tests ---"
git add tests/ 2>/dev/null || echo "  (tests already staged)"

# ------------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------------
echo ""
echo "=========================================="
echo "  Reconciliation Summary"
echo "=========================================="
echo ""

STAGED=$(git diff --cached --stat | tail -1 | grep -oP '\d+ files changed' || echo "0 files changed")
UNSTAGED=$(git status --short | wc -l)
UNTRACKED=$(git ls-files --others --exclude-standard | wc -l)

echo "  Staged  : $STAGED"
echo "  Unstaged: $UNSTAGED (expected: 0)"
echo "  Untracked: $UNTRACKED (expected: artifacts/ only)"
echo ""

if [ "$UNSTAGED" -eq 0 ] && [ "$UNTRACKED" -eq 0 ]; then
  echo "  Working tree fully reconciled."
elif [ "$UNSTAGED" -eq 0 ]; then
  echo "  Working tree reconciled, untracked artifacts remain (expected)."
else
  echo "  WARNING: Some files remain unstaged:"
  git status --short
fi

echo ""
echo "Commits sugeridos:"
echo "  1. git commit -m \"release($RELEASE_TAG): working-tree reconciliation and governance hardening\""
echo "  2. git tag -a \"$RELEASE_TAG\" -m \"Release $RELEASE_TAG\""
