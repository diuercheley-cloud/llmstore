#!/bin/bash
set -e

echo "Generating Release Risk Report..."

REPORT_FILE="reports/release-risk-report-$(date +%Y%m%d-%H%M%S).md"
mkdir -p reports

{
    echo "# Release Risk Report"
    echo "Date: $(date)"
    echo ""
    echo "## Stabilization Rules"
    cat config/stabilization-rules.json
    echo ""
    echo "## Recent Changes (last 10 commits)"
    git log -n 10 --pretty=format:"- %h %s (%an)"
    echo ""
    echo "## Risk Analysis"
} > "$REPORT_FILE"

# Check for new domains
NEW_DOMAINS=$(git diff HEAD~10 --name-only | grep "app/domains/" || true)
if [ -n "$NEW_DOMAINS" ]; then
    echo "- WARNING: New files detected in app/domains/. Verify if this violates 'forbid_new_domains'." >> "$REPORT_FILE"
else
    echo "- OK: No new domains detected in recent history." >> "$REPORT_FILE"
fi

# Check for new services
NEW_SERVICES=$(git diff HEAD~10 --name-only | grep "app/services/" || true)
if [ -n "$NEW_SERVICES" ]; then
    echo "- WARNING: New files detected in app/services/. Verify if this violates 'forbid_new_top_level_services'." >> "$REPORT_FILE"
else
    echo "- OK: No new services detected in recent history." >> "$REPORT_FILE"
fi

# Check for migrations without model changes (or vice versa)
MODELS_CHANGED=$(git diff HEAD~10 --name-only | grep "models.py" || true)
MIGRATIONS_CHANGED=$(git diff HEAD~10 --name-only | grep "alembic/versions" || true)

if [ -n "$MODELS_CHANGED" ] && [ -z "$MIGRATIONS_CHANGED" ]; then
    echo "- CRITICAL: Models changed without corresponding migrations! Violates 'require_migration_for_model_changes'." >> "$REPORT_FILE"
fi

echo "Report generated: $REPORT_FILE"
cat "$REPORT_FILE"
