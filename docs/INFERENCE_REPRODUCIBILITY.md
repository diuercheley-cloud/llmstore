# Inference Reproducibility

Phase 40 adds deterministic inference audit controls with a strict caveat: this stack only offers best-effort reproducibility. It does not promise mathematically exact or bit-perfect replay across different hardware, model builds, quantization formats, backends or tokenizer revisions.

## Replay Model

- Each inference can generate a `CommercialInferenceReproducibilityRecord`.
- The record stores request and response hashes, seed capture, sampling controls, runtime provenance and an immutable audit hash.
- Runtime provenance is normalized into `CommercialInferenceRuntimeSnapshot`.
- Replay attempts are tracked in `CommercialInferenceReplayEvent`.

## Best-Effort Determinism

- Explicit seeds are captured when present.
- If the backend appears seed-capable and no seed is provided, the system derives an implicit seed from the request envelope hash.
- If the backend does not support seed capture and sampling is stochastic, replay support is downgraded.
- `replay_supported=false` means the system can still audit provenance, but cannot claim reproducible replay.

## Drift Detection

The replay verifier checks:

- output drift
- tokenizer drift
- template drift
- runtime drift
- quantization drift

Comparison logic is local only and does not depend on external SaaS:

- exact payload hash match
- normalized text comparison
- token overlap ratio
- lightweight edit distance

## Security Defaults

- Full prompt text is not stored by default.
- Full response payload is not exposed by admin or tenant-safe reports.
- Runtime-sensitive metadata is sanitized before persistence and export.
- Tenant-facing summaries only expose hashes, support flags, replay status and provenance summaries.

## Admin Endpoints

- `GET /admin/inference/reproducibility`
- `GET /admin/inference/reproducibility/{id}`
- `POST /admin/inference/replay/{id}`
- `GET /admin/inference/replay-events`
- `GET /admin/inference/runtime-snapshots`
- `GET /admin/inference/reproducibility/status`

## Limitations

- Cross-backend replay is disabled by default.
- Cross-hardware exact replay is not guaranteed.
- Different tokenizer versions can invalidate prompt equivalence even when the visible text looks unchanged.
- Quantization drift can produce output drift with the same seed and sampling parameters.

## Validation

```bash
pytest -q \
  tests/test_inference_reproducibility.py \
  tests/test_replay_verification.py \
  tests/test_runtime_snapshot_drift.py \
  tests/test_runtime_model_integrity.py

bash -n scripts/validate-inference-reproducibility.sh
bash -n scripts/validate-model-integrity-monitor.sh
```
