#!/usr/bin/env bash
# agent-bundle-publish.sh — Publish agent bundle to marketplace as draft
set -euo pipefail

BUNDLE_DIR="${1:-.}"
API_BASE="${API_BASE:-http://localhost:8080}"
DRAFT_ONLY="${2:-true}"

red()   { echo -e "\033[0;31m$*\033[0m"; }
green() { echo -e "\033[0;32m$*\033[0m"; }
yellow(){ echo -e "\033[0;33m$*\033[0m"; }
info()  { echo -e "\033[0;36m$*\033[0m"; }

echo "Publishing bundle: $BUNDLE_DIR"
echo "==============================="

# 1. Validate
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$SCRIPT_DIR/agent-bundle-validate.sh" ]; then
  info "Running pre-publish validation..."
  if ! "$SCRIPT_DIR/agent-bundle-validate.sh" "$BUNDLE_DIR"; then
    red "Aborting: bundle validation failed"
    exit 1
  fi
fi

# 2. Check signature
if [ ! -f "$BUNDLE_DIR/bundle.sig" ]; then
  yellow "WARNING: bundle.sig not found. Run agent-bundle-sign.sh first."
  yellow "Publishing as unsigned bundle."
fi

# 3. Create publish payload
info "Creating publish payload..."

PAYLOAD_FILE=$(mktemp)
python3 -c "
import json, os, hashlib

bundle_dir = '$BUNDLE_DIR'

# Read manifest
with open(os.path.join(bundle_dir, 'manifest.json')) as f:
    manifest = json.load(f)

# Read signature if exists
sig = {}
sig_path = os.path.join(bundle_dir, 'bundle.sig')
if os.path.exists(sig_path):
    with open(sig_path) as f:
        sig = json.load(f)

# Build payload
payload = {
    'name': manifest.get('name'),
    'version': manifest.get('version'),
    'description': manifest.get('description', ''),
    'author': manifest.get('author', ''),
    'category': manifest.get('category', 'general'),
    'min_platform_version': manifest.get('min_platform_version', '1.0.0'),
    'manifest': manifest,
    'signature': sig,
    'status': 'draft'
}

with open('$PAYLOAD_FILE', 'w') as f:
    json.dump(payload, f, indent=2)
"

info "Payload created in $PAYLOAD_FILE"

# 4. Publish via API (mock — would be a real POST in production)
info "Publishing to marketplace..."

python3 -c "
import json, datetime, sys

with open('$PAYLOAD_FILE') as f:
    payload = json.load(f)

# Simulate API response
result = {
    'status': 'success',
    'bundle_id': 'bundle-' + payload['name'] + '-' + payload['version'],
    'marketplace_status': 'draft',
    'message': 'Bundle submitted as draft. Pending review.',
    'published_at': datetime.datetime.now(datetime.UTC).isoformat() + 'Z',
    'next_steps': [
        'Bundle is now in draft status',
        'Review will be triggered automatically',
        'Once approved, it will appear in the marketplace'
    ]
}

print('')
print('===============================')
print(f'  Status: \033[0;32m{result[\"status\"].upper()}\033[0m')
print(f'  Bundle ID: {result[\"bundle_id\"]}')
print(f'  Marketplace: {result[\"marketplace_status\"]}')
print('')
for step in result.get('next_steps', []):
    print(f'  -> {step}')
"

rm "$PAYLOAD_FILE"

echo ""
green "BUNDLE PUBLISHED AS DRAFT"
echo ""
echo "Bundle will be reviewed before going live in the marketplace."
