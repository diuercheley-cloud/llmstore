# Local Production Validation Summary

**Result: SUCCESS**

## Metadata

- **Version:** v1.9.3-stabilization-hardening
- **Branch:** release/v1.8.3
- **Commit:** 555fd17cdbd1461ee7b8a74d2b77289672ecfe58
- **Base URL:** http://localhost:18080
- **Start Time:** 2026-05-19T22:56:32Z
- **End Time:** 2026-05-19T22:58:25Z
- **Total Duration:** 113s

## Environment

- LOCALHOST_MODE: `True`
- LOCAL_BILLING_MODE: `False`
- RAG_ENABLED: `True`
- LM_STUDIO_CONFIGURED: `False`
- LM_STUDIO_ONLINE: `true`
- curl_mode: `host`
- orphan_containers_detected: `False`

## Execution Summary

| Script | Status | Critical | Duration | Log |
| :--- | :--- | :---: | :---: | :--- |
| `check-alembic-integrity.sh` | OK | Yes | 0s | [view](logs/check-alembic-integrity.sh.log) |
| `validate-localhost-mode.sh` | OK | Yes | 8s | [view](logs/validate-localhost-mode.sh.log) |
| `validate-status-local.sh` | OK | Yes | 12s | [view](logs/validate-status-local.sh.log) |
| `validate-admin-lab-local.sh` | SKIP | No | 0s | [view](logs/validate-admin-lab-local.sh.log) |
| `validate-usable-chat-model-local.sh` | OK | Yes | 0s | [view](logs/validate-usable-chat-model-local.sh.log) |
| `validate-lmstudio-backend.sh` | OK | No | 7s | [view](logs/validate-lmstudio-backend.sh.log) |
| `validate-routing-local.sh` | OK | Yes | 6s | [view](logs/validate-routing-local.sh.log) |
| `validate-plan-queues.sh` | SKIP | No | 0s | [view](logs/validate-plan-queues.sh.log) |
| `validate-client-portal-local.sh` | SKIP | No | 0s | [view](logs/validate-client-portal-local.sh.log) |
| `validate-api-keys-local.sh` | OK | Yes | 10s | [view](logs/validate-api-keys-local.sh.log) |
| `validate-rag-local-multiclient.sh` | SKIP | No | 0s | [view](logs/validate-rag-local-multiclient.sh.log) |
| `validate-local-billing.sh` | SKIP | No | 0s | [view](logs/validate-local-billing.sh.log) |
| `validate-local-docs.sh` | OK | Yes | 2s | [view](logs/validate-local-docs.sh.log) |
| `validate-observability-local.sh` | SKIP | No | 0s | [view](logs/validate-observability-local.sh.log) |

## Warnings & Skips

- **validate-admin-lab-local.sh**: Skipped in quick validation mode
- **validate-plan-queues.sh**: Skipped in quick validation mode
- **validate-client-portal-local.sh**: Skipped in quick validation mode
- **validate-rag-local-multiclient.sh**: Skipped in quick validation mode
- **validate-local-billing.sh**: Skipped in quick validation mode
- **validate-observability-local.sh**: Skipped in quick validation mode

## Test Suite

- pytest exit code: `0`
- total: `48`
- passed: `45`
- failed: `0`
- errors: `0`
- skipped: `3`
- log: [view](logs/pytest.log)

## How to reproduce

```bash
./scripts/validate-local-production-full.sh
```

## Useful commands

- Check logs: `ls -R /home/kleber/llm-inference-stack/artifacts/local-production-validation/20260519T195632/logs/`
- Tail all logs: `tail -f /home/kleber/llm-inference-stack/artifacts/local-production-validation/20260519T195632/logs/*.log`
- Check services: `docker compose ps`

## Out of scope

- Real PSP (Stripe/MercadoPago) integration tests.
- External DNS/SSL validation (handled by cloud provider).
- GPU stress testing (requires dedicated environment).

## Conclusion

The local production environment is healthy and ready for staging deployment.