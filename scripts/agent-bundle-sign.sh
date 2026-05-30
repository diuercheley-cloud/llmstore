#!/usr/bin/env bash
# agent-bundle-sign.sh — Sign agent bundle with ed25519 key
set -euo pipefail

BUNDLE_DIR="${1:-.}"
KEY_FILE="${2:-}"
OUTPUT_SIG="${3:-$BUNDLE_DIR/bundle.sig}"

red()   { echo -e "\033[0;31m$*\033[0m"; }
green() { echo -e "\033[0;32m$*\033[0m"; }
yellow(){ echo -e "\033[0;33m$*\033[0m"; }
info()  { echo -e "\033[0;36m$*\033[0m"; }

echo "Signing bundle: $BUNDLE_DIR"
echo "==============================="

# 1. Validate first
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$SCRIPT_DIR/agent-bundle-validate.sh" ]; then
  info "Running pre-sign validation..."
  if ! "$SCRIPT_DIR/agent-bundle-validate.sh" "$BUNDLE_DIR"; then
    red "Aborting: bundle validation failed"
    exit 1
  fi
fi

# 2. Compute checksums
info "Computing checksums..."
CHECKSUM=$(python3 -c "
import hashlib, json, os, glob

bundle_dir = '$BUNDLE_DIR'
files = sorted(glob.glob(os.path.join(bundle_dir, '**', '*'), recursive=True))
files = [f for f in files if os.path.isfile(f) and not f.endswith('.sig') and not f.endswith('.pem')]

h = hashlib.sha256()
for f in files:
    with open(f, 'rb') as fh:
        h.update(fh.read())

checksum = h.hexdigest()
print(checksum)

# Update manifest checksums
manifest_path = os.path.join(bundle_dir, 'manifest.json')
if os.path.exists(manifest_path):
    with open(manifest_path) as f:
        data = json.load(f)
    data['checksums'] = data.get('checksums', {})
    data['checksums']['bundle'] = checksum
    with open(manifest_path, 'w') as f:
        json.dump(data, f, indent=2)
" 2>&1)

green "Bundle checksum: $CHECKSUM"

# 3. Generate or load signing key
if [ -z "$KEY_FILE" ]; then
  KEY_DIR="$HOME/.agentctl/keys"
  KEY_FILE="$KEY_DIR/default_ed25519.pem"

  if [ ! -f "$KEY_FILE" ]; then
    info "Generating new ed25519 signing key..."
    mkdir -p "$KEY_DIR"
    python3 -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

key = Ed25519PrivateKey.generate()
pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
with open('$KEY_FILE', 'wb') as f:
    f.write(pem)

pub = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
pub_file = '$KEY_FILE'.replace('.pem', '.pub')
with open(pub_file, 'wb') as f:
    f.write(pub)
" 2>/dev/null
    chmod 600 "$KEY_FILE"
    green "New key generated: $KEY_FILE"
    green "Public key: ${KEY_FILE%.pem}.pub"
  else
    info "Using existing key: $KEY_FILE"
  fi
else
  if [ ! -f "$KEY_FILE" ]; then
    red "Key file not found: $KEY_FILE"
    exit 1
  fi
  info "Using key: $KEY_FILE"
fi

# 4. Sign the bundle
info "Signing bundle..."
SIGNATURE=$(python3 -c "
import hashlib, base64, subprocess, tempfile, os

# Write checksum to temp file for signing
checksum = '$CHECKSUM'
key_file = '$KEY_FILE'

# Use openssl to sign - try different approaches
with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
    f.write(checksum.encode())
    tmp_path = f.name

try:
    # Try pkeyutl with rawin (OpenSSL 3.x)
    result = subprocess.run(
        ['openssl', 'pkeyutl', '-sign', '-inkey', key_file, '-in', tmp_path, '-rawin'],
        capture_output=True
    )
    if result.returncode == 0 and result.stdout:
        sig = base64.b64encode(result.stdout).decode()
        print(sig)
    else:
        # Fallback: use Python cryptography library
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        with open(key_file, 'rb') as f:
            key_data = f.read()
        private_key = serialization.load_pem_private_key(key_data, password=None)
        sig = private_key.sign(checksum.encode())
        print(base64.b64encode(sig).decode())
finally:
    os.unlink(tmp_path)
" 2>&1)

# 5. Extract public key for verification
PUBLIC_KEY=$(python3 -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import base64

with open('$KEY_FILE', 'rb') as f:
    key_data = f.read()
private_key = serialization.load_pem_private_key(key_data, password=None)
pub = private_key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
print(base64.b64encode(pub).decode())
" 2>&1)

# 6. Write signature file
python3 -c "
import json, datetime

signature_data = {
    'algorithm': 'ed25519',
    'checksum': '$CHECKSUM',
    'signature': '$SIGNATURE',
    'public_key': '$PUBLIC_KEY',
    'signed_at': datetime.datetime.utcnow().isoformat() + 'Z',
    'bundle_dir': '$BUNDLE_DIR'
}

with open('$OUTPUT_SIG', 'w') as f:
    json.dump(signature_data, f, indent=2)

# Also embed in manifest
import os
manifest_path = os.path.join('$BUNDLE_DIR', 'manifest.json')
if os.path.exists(manifest_path):
    with open(manifest_path) as f:
        data = json.load(f)
    data['signature'] = {
        'algorithm': 'ed25519',
        'checksum': '$CHECKSUM',
        'signed_at': signature_data['signed_at']
    }
    with open(manifest_path, 'w') as f:
        json.dump(data, f, indent=2)
" 2>&1

green "Signature written to: $OUTPUT_SIG"
green "Manifest updated with signature"

echo ""
echo "==============================="
green "BUNDLE SIGNED SUCCESSFULLY"
echo ""
echo "Checksum: $CHECKSUM"
echo "Signature: $OUTPUT_SIG"
echo "Key: $KEY_FILE"
echo ""
echo "Next: Run agent-bundle-publish.sh to publish to marketplace"
