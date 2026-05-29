#!/bin/bash

# Archive Deprecated Surface
# Moves identified obsolete scripts and services to an artifacts folder to avoid violating freeze rules.

echo "Archiving deprecated surface components..."

# Create archive structure under artifacts (which is allowed)
ROOT_ARCHIVE="artifacts/archive/$(date +%Y%m%d)"
mkdir -p "$ROOT_ARCHIVE/scripts"
mkdir -p "$ROOT_ARCHIVE/services"

# 1. Archive Obsolete Scripts
SCRIPTS_TO_ARCHIVE=(
    "scripts/audit-v1.6-release-line.sh"
    "scripts/diagnose-v1.7-warnings.sh"
    "scripts/generate-v1.7-release-checklist-status.sh"
    "scripts/prepare-v1.7-release-bundle.sh"
    "scripts/run-v1.7-release-checklist.sh"
    "scripts/validate-readiness-cleanup-v1.6.3.sh"
    "scripts/validate-security-cleanup-v1.5.4.sh"
    "scripts/validate-v1.6-release-line-audit.sh"
    "scripts/validate-v1.7-final-local.sh"
    "scripts/validate-v1.7-final-report.sh"
    "scripts/validate-v1.7-go-no-go-summary.sh"
    "scripts/validate-v1.7-release-bundle.sh"
    "scripts/validate-v1.7-release-checklist.sh"
    "scripts/validate-v1.7-release-notes.sh"
    "scripts/validate-v1.7-warning-cleanup.sh"
)

# Move from temporary archive locations if they exist
if [ -d "scripts/archive" ]; then
    mv scripts/archive/* "$ROOT_ARCHIVE/scripts/" 2>/dev/null
    rmdir "scripts/archive"
fi

if [ -d "archive/platform-consolidation" ]; then
    # If they were in the previous root archive
    find archive/platform-consolidation -name "*.sh" -exec mv {} "$ROOT_ARCHIVE/scripts/" \;
    find archive/platform-consolidation -name "*.py" -exec mv {} "$ROOT_ARCHIVE/services/" \;
    rm -rf archive/platform-consolidation
fi

for script in "${SCRIPTS_TO_ARCHIVE[@]}"; do
    if [ -f "$script" ]; then
        mv "$script" "$ROOT_ARCHIVE/scripts/"
        echo "Archived script: $script"
    fi
done

# 2. Archive Deprecated Services (Dead Code)
SERVICES_TO_ARCHIVE=(
    "control_plane/app/services/event_service.py"
    "control_plane/app/services/tts_readiness.py"
    "control_plane/app/services/governance/release_engineering/release_notes_generator.py"
    "control_plane/app/services/governance/release_engineering/release_replay_verifier.py"
    "control_plane/app/services/governance/human_governance/approval_quorum_service.py"
    "control_plane/app/services/governance/human_governance/escalation_service.py"
    "control_plane/app/services/governance/human_governance/review_workflow_service.py"
    "control_plane/app/services/governance/human_governance/separation_of_duties.py"
    "control_plane/app/services/governance/data_governance/data_lineage_service.py"
    "control_plane/app/services/governance/data_governance/data_zone_service.py"
    "control_plane/app/services/governance/data_governance/export_governance_service.py"
    "control_plane/app/services/governance/data_governance/retention_policy_service.py"
)

# Move from previous archive location
if [ -d "control_plane/app/services/archive" ]; then
    mv control_plane/app/services/archive/* "$ROOT_ARCHIVE/services/" 2>/dev/null
    rmdir "control_plane/app/services/archive"
fi

for service in "${SERVICES_TO_ARCHIVE[@]}"; do
    if [ -f "$service" ]; then
        mv "$service" "$ROOT_ARCHIVE/services/"
        echo "Archived service: $service"
    fi
done

echo "Archiving complete. All components moved to $ROOT_ARCHIVE"
