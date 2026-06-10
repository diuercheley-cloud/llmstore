#!/usr/bin/env bash
# agent-bundle-validate.sh — Validate agent bundle manifest and structure
set -euo pipefail

BUNDLE_DIR="${1:-.}"
ERRORS=0
WARNINGS=0

red()   { echo -e "\033[0;31m$*\033[0m"; }
green() { echo -e "\033[0;32m$*\033[0m"; }
yellow(){ echo -e "\033[0;33m$*\033[0m"; }
info()  { echo -e "\033[0;36m$*\033[0m"; }

echo "Validating bundle: $BUNDLE_DIR"
echo "==============================="

# 1. Check manifest.json exists
if [ ! -f "$BUNDLE_DIR/manifest.json" ]; then
  red "FAIL: manifest.json not found in $BUNDLE_DIR"
  exit 1
fi
green "OK: manifest.json found"

# 2. Parse manifest
if ! command -v python3 &>/dev/null; then
  red "FAIL: python3 required for validation"
  exit 1
fi

VALIDATION_RESULT=$(python3 -c "
import json, sys, os

errors = []
warnings = []

with open('$BUNDLE_DIR/manifest.json') as f:
    try:
        data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f'Invalid JSON: {e}')
        json.dumps({'errors': errors, 'warnings': warnings})
        sys.exit(0)

# Required fields
required = ['name', 'version', 'agent_definition']
for field in required:
    if field not in data:
        errors.append(f'Missing required field: {field}')

# Version format
if 'version' in data:
    import re
    if not re.match(r'^\d+\.\d+\.\d+', str(data['version'])):
        warnings.append(f'Version \"{data[\"version\"]}\" is not semver format')

# agent_definition check
if 'agent_definition' in data:
    ad = data['agent_definition']
    if not isinstance(ad, dict):
        errors.append('agent_definition must be an object')
    else:
        for f in ['instructions', 'model_id']:
            if f not in ad:
                errors.append(f'agent_definition missing: {f}')

# tool_requirements check
if 'tool_requirements' in data:
    if not isinstance(data['tool_requirements'], list):
        errors.append('tool_requirements must be an array')

# checksums
if 'checksums' not in data:
    warnings.append('No checksums defined (recommended for integrity)')

# signature
if 'signature' not in data:
    warnings.append('No signature (required for marketplace publish)')

# min_platform_version
if 'min_platform_version' not in data:
    warnings.append('No min_platform_version defined')

# Directory structure
if not os.path.isdir('$BUNDLE_DIR/src'):
    warnings.append('src/ directory not found')
if not os.path.isdir('$BUNDLE_DIR/tests'):
    warnings.append('tests/ directory not found')

json.dump({'errors': errors, 'warnings': warnings}, sys.stdout)
" 2>&1)

# 3. Parse validation result
ERROR_COUNT=$(echo "$VALIDATION_RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['errors']))")
WARN_COUNT=$(echo "$VALIDATION_RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['warnings']))")

# Print errors
if [ "$ERROR_COUNT" -gt 0 ]; then
  echo "$VALIDATION_RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for e in d['errors']:
    print(f'  \033[0;31mERROR: {e}\033[0m')
"
  ERRORS=$((ERRORS + ERROR_COUNT))
fi

# Print warnings
if [ "$WARN_COUNT" -gt 0 ]; then
  echo "$VALIDATION_RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for w in d['warnings']:
    print(f'  \033[0;33mWARN: {w}\033[0m')
"
  WARNINGS=$((WARNINGS + WARN_COUNT))
fi

echo ""
echo "==============================="
if [ "$ERRORS" -gt 0 ]; then
  red "FAILED: $ERRORS error(s), $WARNINGS warning(s)"
  exit 1
elif [ "$WARNINGS" -gt 0 ]; then
  yellow "PASSED with $WARNINGS warning(s)"
  exit 0
else
  green "PASSED: All checks passed"
  exit 0
fi
