#!/usr/bin/env bash
set -euo pipefail

# ==========================================================================
# Phase 42: Validate Verifiable AI Execution Proofs + Merkle Audit Timelines
# ==========================================================================

BASE_URL="${BASE_URL:-http://localhost:8080}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); echo "  [PASS] $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  [FAIL] $1"; }

echo "========================================"
echo " Phase 42: Execution Proofs Validation"
echo "========================================"
echo ""

# --- 1. Compile-check all source files ---
echo "[1/8] Compile-checking source files..."
for f in \
  control_plane/app/models/commercial_merkle_timelines.py \
  control_plane/app/services/inference/merkle_timelines.py \
  control_plane/app/services/inference/execution_proofs.py \
  control_plane/app/api/commercial_execution_proofs_admin.py \
  control_plane/app/api/commercial_execution_proofs_portal.py; do
  if python3 -m py_compile "$f" 2>/dev/null; then
    pass "compile $f"
  else
    fail "compile $f"
  fi
done

# --- 2. Verify test files exist ---
echo ""
echo "[2/8] Checking test files..."
for f in \
  tests/test_merkle_timelines.py \
  tests/test_execution_proofs.py \
  tests/test_proof_verification.py; do
  if [ -f "$f" ]; then
    pass "exists $f"
  else
    fail "missing $f"
  fi
done

# --- 3. Verify docs ---
echo ""
echo "[3/8] Checking documentation..."
if [ -f docs/VERIFIABLE_EXECUTION_PROOFS.md ]; then
  pass "docs/VERIFIABLE_EXECUTION_PROOFS.md exists"
else
  fail "docs/VERIFIABLE_EXECUTION_PROOFS.md missing"
fi

# --- 4. Verify migration ---
echo ""
echo "[4/8] Checking Alembic migration..."
if ls control_plane/alembic/versions/*phase42* 2>/dev/null | grep -q .; then
  pass "Phase 42 migration found"
else
  fail "Phase 42 migration missing"
fi

# --- 5. No prompt/response leakage ---
echo ""
echo "[5/8] Checking for prompt/response leakage..."
LEAKS=0
for f in \
  control_plane/app/services/inference/execution_proofs.py \
  control_plane/app/api/commercial_execution_proofs_admin.py \
  control_plane/app/api/commercial_execution_proofs_portal.py; do
  # Check for accidental prompt/response field exposure (excluding sanitizer references)
  if grep -n '"prompt"\|"response"\|"completion"\|"messages"' "$f" 2>/dev/null | grep -v '_sanitize\|sanitize_metadata\|#\|forbidden\|keys_to_remove\|assert.*not' >/dev/null 2>&1; then
    LEAKS=$((LEAKS + 1))
  fi
done
if [ "$LEAKS" -eq 0 ]; then
  pass "No prompt/response leakage detected in services"
else
  fail "Potential prompt/response leakage detected ($LEAKS files)"
fi

# --- 6. Verify Merkle tree determinism (inline Python test) ---
echo ""
echo "[6/8] Verifying Merkle tree determinism..."
PYTHONPATH="control_plane" .venv/bin/python3 -c "
from app.services.inference.merkle_timelines import (
    canonical_leaf_hash, calculate_merkle_root, generate_inclusion_proof,
    verify_inclusion_proof, seal_timeline, validate_timeline_chain,
    summarize_timelines, build_merkle_tree, MerkleError
)
import hashlib

# Determinism
leaves = [canonical_leaf_hash(f'id-{i}', 'receipt', {'idx': i}) for i in range(8)]
r1 = calculate_merkle_root(leaves)
r2 = calculate_merkle_root(leaves)
assert r1 == r2, 'Merkle root not deterministic'

# Inclusion proof valid
proof = generate_inclusion_proof(3, leaves)
assert verify_inclusion_proof(proof), 'Valid inclusion proof failed'

# Inclusion proof invalid after tamper
from app.services.inference.merkle_timelines import MerkleInclusionProof
tampered = MerkleInclusionProof(
    leaf_hash=canonical_leaf_hash('tampered', 'x', {}),
    leaf_index=proof.leaf_index,
    steps=proof.steps,
    root=proof.root,
)
assert not verify_inclusion_proof(tampered), 'Tampered proof should fail'

# Seal timeline
root = seal_timeline(leaves)
assert len(root) == 64

# Seal with chain
prev = hashlib.sha256(b'prev').hexdigest()
chained = seal_timeline(leaves, prev)
assert chained != root, 'Chain should differ'

# Timeline summary
summary = summarize_timelines([
    {'leaf_count': 10, 'status': 'sealed', 'merkle_root': 'r1'},
    {'leaf_count': 5, 'status': 'verified', 'merkle_root': 'r2', 'previous_timeline_root': 'r1'},
])
assert summary['chain_valid'] is True
assert summary['total_leaves'] == 15

print('All inline Merkle assertions passed')
" && pass "Merkle determinism + inclusion proof + tamper detection" \
  || fail "Merkle determinism test failed"

# --- 7. Verify sanitized export (inline Python test) ---
echo ""
echo "[7/8] Verifying sanitized export..."
PYTHONPATH="control_plane" .venv/bin/python3 -c "
from app.services.inference.execution_proofs import _sanitize_metadata
meta = {
    'client_id': 'c1',
    'model': 'm1',
    'prompt': 'secret prompt',
    'response': 'secret response',
    'messages': [{'role': 'user'}],
    'completion': 'secret',
    'content': 'secret',
}
clean = _sanitize_metadata(meta)
for k in ('prompt', 'response', 'messages', 'completion', 'content'):
    assert k not in clean, f'{k} leaked'
assert 'client_id' in clean
assert 'model' in clean
print('Sanitization OK: no sensitive fields in export')
" && pass "Export sanitization validated" \
  || fail "Export sanitization test failed"

# --- 8. Live endpoint validation (if ADMIN_TOKEN set) ---
echo ""
echo "[8/8] Live endpoint validation..."
if [ -z "${ADMIN_TOKEN}" ]; then
  echo "  [SKIP] ADMIN_TOKEN not set; skipping live endpoint tests"
else
  auth_header="X-Admin-Token: ${ADMIN_TOKEN}"

  # Timelines list
  if curl -fsS "${BASE_URL}/admin/inference/proofs/timelines" -H "${auth_header}" >/dev/null 2>&1; then
    pass "GET /admin/inference/proofs/timelines"
  else
    fail "GET /admin/inference/proofs/timelines"
  fi

  # Proofs list
  if curl -fsS "${BASE_URL}/admin/inference/proofs/proofs" -H "${auth_header}" >/dev/null 2>&1; then
    pass "GET /admin/inference/proofs/proofs"
  else
    fail "GET /admin/inference/proofs/proofs"
  fi

  # Portal proofs list
  if curl -fsS "${BASE_URL}/portal/inference/proofs/proofs" >/dev/null 2>&1; then
    pass "GET /portal/inference/proofs/proofs"
  else
    fail "GET /portal/inference/proofs/proofs"
  fi

  # Build timeline
  BUILD_RESP=$(curl -sS -X POST "${BASE_URL}/admin/inference/proofs/timelines/build" \
    -H "${auth_header}" \
    -H "Content-Type: application/json" \
    -d '{"timeline_type":"inference_receipts","window_minutes":60}' 2>&1)
  if echo "$BUILD_RESP" | grep -q '"id"'; then
    pass "POST /admin/inference/proofs/timelines/build"
    TL_ID=$(echo "$BUILD_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || true)
    if [ -n "$TL_ID" ]; then
      # Seal
      if curl -fsS -X POST "${BASE_URL}/admin/inference/proofs/timelines/${TL_ID}/seal" -H "${auth_header}" >/dev/null 2>&1; then
        pass "POST seal timeline"
      else
        fail "POST seal timeline"
      fi
      # Verify
      if curl -fsS -X POST "${BASE_URL}/admin/inference/proofs/timelines/${TL_ID}/verify" -H "${auth_header}" >/dev/null 2>&1; then
        pass "POST verify timeline"
      else
        fail "POST verify timeline"
      fi
    fi
  else
    echo "  [SKIP] Build timeline returned no data (may need receipts)"
  fi
fi

echo ""
echo "========================================"
echo " Results: ${PASS} passed, ${FAIL} failed"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
