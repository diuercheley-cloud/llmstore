#!/usr/bin/env bash
set -euo pipefail

# ==========================================================================
# Phase 43: Validate Public Verifier CLI + Offline Verification Tool
# ==========================================================================

echo "========================================"
echo " Phase 43: Public Verifier Validation"
echo "========================================"
echo ""

# 1. Check directory structure
echo "[1/5] Checking directory structure..."
test -d tools/public_verifier
test -f tools/public_verifier/verifier_cli.py
test -f tools/public_verifier/verifier_core.py
echo "  [PASS] Structure OK"

# 2. Compile check
echo ""
echo "[2/5] Compile-checking source files..."
for f in tools/public_verifier/*.py; do
    .venv/bin/python3 -m py_compile "$f" && echo "  [PASS] $f" || (echo "  [FAIL] $f" && exit 1)
done

# 3. Create dummy proof for live test
echo ""
echo "[3/5] Creating sample proof for CLI validation..."
.venv/bin/python3 -c "
import json, hashlib
def sha256_hex(data): return hashlib.sha256(data.encode('utf-8')).hexdigest()
def pair_hash(l, r): return hashlib.sha256(bytes.fromhex(l) + bytes.fromhex(r)).hexdigest()

l1 = sha256_hex('leaf1')
l2 = sha256_hex('leaf2')
root = pair_hash(l1, l2)

data = {
    'proof_type': 'execution',
    'verification_status': 'pending',
    'timeline_root': root,
    'previous_timeline_root': sha256_hex('prev_root'),
    'merkle_inclusion_proof': {
        'leaf_hash': l1,
        'leaf_index': 0,
        'steps': [{'sibling_hash': l2, 'is_right': False}],
        'root': root
    },
    'replay_verification_summary': {
        'chain_valid': True,
        'signature_valid': True
    }
}
# Hash must exclude proof_hash and verification_status
to_hash = data.copy()
to_hash.pop('proof_hash', None)
to_hash.pop('verification_status', None)
canonical = json.dumps(to_hash, sort_keys=True, separators=(',', ':'))
data['proof_hash'] = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
with open('sample_proof.json', 'w') as f:
    json.dump(data, f)
"

# 4. Run CLI verify
echo ""
echo "[4/5] Running CLI verify command..."
PYTHONPATH=. .venv/bin/python3 -m tools.public_verifier.verifier_cli verify sample_proof.json --export report.json
if [ -f report.json ]; then
    echo "  [PASS] CLI Verify command successful"
else
    echo "  [FAIL] CLI Verify command failed to produce report"
    exit 1
fi

# 5. Run tests
echo ""
echo "[5/5] Running unit tests..."
PYTHONPATH=. .venv/bin/python3 -m pytest -q tools/public_verifier/tests/test_verifier_core.py
echo "  [PASS] Unit tests OK"

echo ""
echo "========================================"
echo " Results: ALL PASSED"
echo "========================================"

# Cleanup
rm sample_proof.json report.json
