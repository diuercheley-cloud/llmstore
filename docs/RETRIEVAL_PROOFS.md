---
owner: platform-ops
status: consolidated
---

# Retrieval Proofs

Phase 49 adds verifiable retrieval proofs for regulated RAG.

## Guarantees

- Proves which chunk hashes and document hashes participated in retrieval.
- Proves which policy outcome allowed the retrieval.
- Proves the exact sanitized retrieval context hash sent to the model.
- Produces Merkle-backed inclusion proofs without storing prompt or response plaintext.

## Main objects

- `CommercialRetrievalProof`
- `CommercialRetrievalMerkleLeaf`
- `CommercialRetrievalReplayRecord`

## Verifier support

Public verifier and public attestation gateway support:

- retrieval proof verification
- lineage consistency verification
- retrieval replay verification

## Validation

```bash
pytest -q tests/test_retrieval_proofs.py
bash -n scripts/validators/validate-retrieval-proofs.sh
make validate-retrieval-proofs
```
