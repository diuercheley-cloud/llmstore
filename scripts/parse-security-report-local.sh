#!/bin/bash
# scripts/parse-security-report-local.sh
# Parses security-report.json and prints a safe summary.

set -e

REPORT_JSON=$1
FORMAT=${2:-text} # text or md

if [ -z "$REPORT_JSON" ]; then
    echo "Usage: $0 <path-to-security-report.json> [text|md]"
    exit 1
fi

if [ ! -f "$REPORT_JSON" ]; then
    echo "Error: File not found: $REPORT_JSON"
    exit 1
fi

# Function to mask secrets in evidence
mask_evidence() {
    # Masks strings like ADMIN_TOKEN=... or hex strings
    # Improved to handle hyphens and common token prefixes
    sed -E 's/([A-Z0-9_]+=)[A-Za-z0-9\._-]+/\1[MASKED]/g' | \
    sed -E 's/[a-f0-9]{32,}/[MASKED-HEX]/g'
}

SCORE=$(jq -r '.score' "$REPORT_JSON")
PASS=$(jq -r '.totals.pass' "$REPORT_JSON")
WARN=$(jq -r '.totals.warn' "$REPORT_JSON")
FAIL=$(jq -r '.totals.fail' "$REPORT_JSON")
SKIP=$(jq -r '.totals.skip' "$REPORT_JSON")

if [ "$FORMAT" == "text" ]; then
    echo "Security Report Summary"
    echo "======================="
    echo "Score: $SCORE"
    echo "Totals: PASS=$PASS, WARN=$WARN, FAIL=$FAIL, SKIP=$SKIP"
    echo ""
    echo "Detailed Issues:"
    jq -c '.checks[] | select(.status != "pass")' "$REPORT_JSON" | while read -r check; do
        ID=$(echo "$check" | jq -r '.id')
        STATUS=$(echo "$check" | jq -r '.status')
        TITLE=$(echo "$check" | jq -r '.title')
        DETAILS=$(echo "$check" | jq -r '.details')
        EVIDENCE=$(echo "$check" | jq -r '.evidence' | mask_evidence)
        
        echo "[$STATUS] $ID: $TITLE"
        echo "  Details: $DETAILS"
        if [ -n "$EVIDENCE" ]; then
            echo "  Evidence: $EVIDENCE"
        fi
        echo ""
    done
elif [ "$FORMAT" == "md" ]; then
    echo "# Security Report Summary"
    echo ""
    echo "- **Score:** $SCORE"
    echo "- **Totals:** PASS=$PASS, WARN=$WARN, FAIL=$FAIL, SKIP=$SKIP"
    echo ""
    echo "## Issues"
    echo ""
    echo "| Status | ID | Title | Details |"
    echo "|--------|----|-------|---------|"
    jq -r '.checks[] | select(.status != "pass") | [ .status, .id, .title, .details ] | @tsv' "$REPORT_JSON" | while IFS=$'\t' read -r status id title details; do
        echo "| $status | $id | $title | $details |"
    done
    echo ""
    echo "## Evidence (Masked)"
    echo ""
    jq -c '.checks[] | select(.status != "pass" and .evidence != "")' "$REPORT_JSON" | while read -r check; do
        ID=$(echo "$check" | jq -r '.id')
        EVIDENCE=$(echo "$check" | jq -r '.evidence' | mask_evidence)
        echo "### $ID"
        echo "\`\`\`"
        echo "$EVIDENCE"
        echo "\`\`\`"
    done
fi
