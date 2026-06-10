# Local Production Validation Summary

**Result: FAILED**

## Metadata

- **Version:** v2.0.7-multi-agent-13-g482bfc9
- **Branch:** 2.0.9
- **Commit:** 482bfc955de35d092763721a21aad3d99ddb21db
- **Base URL:** http://localhost:18080
- **Start Time:** 2026-06-10T00:40:59Z
- **End Time:** 2026-06-10T00:41:07Z
- **Total Duration:** 8s

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
| `validate-localhost-mode.sh` | ERROR | Yes | 0s | [view](logs/validate-localhost-mode.sh.log) |
| `validate-status-local.sh` | ERROR | Yes | 0s | [view](logs/validate-status-local.sh.log) |
| `validate-admin-lab-local.sh` | SKIP | No | 0s | [view](logs/validate-admin-lab-local.sh.log) |
| `validate-usable-chat-model-local.sh` | OK | Yes | 0s | [view](logs/validate-usable-chat-model-local.sh.log) |
| `validate-lmstudio-backend.sh` | WARN | No | 0s | [view](logs/validate-lmstudio-backend.sh.log) |
| `validate-routing-local.sh` | ERROR | Yes | 0s | [view](logs/validate-routing-local.sh.log) |
| `validate-plan-queues.sh` | SKIP | No | 0s | [view](logs/validate-plan-queues.sh.log) |
| `validate-client-portal-local.sh` | SKIP | No | 0s | [view](logs/validate-client-portal-local.sh.log) |
| `validate-api-keys-local.sh` | OK | Yes | 0s | [view](logs/validate-api-keys-local.sh.log) |
| `validate-rag-local-multiclient.sh` | SKIP | No | 0s | [view](logs/validate-rag-local-multiclient.sh.log) |
| `validate-local-billing.sh` | SKIP | No | 0s | [view](logs/validate-local-billing.sh.log) |
| `validate-local-docs.sh` | ERROR | Yes | 0s | [view](logs/validate-local-docs.sh.log) |
| `check-feature-flags.sh` | ERROR | Yes | 0s | [view](logs/check-feature-flags.sh.log) |
| `validate-observability-local.sh` | SKIP | No | 0s | [view](logs/validate-observability-local.sh.log) |

## Warnings & Skips

- **validate-admin-lab-local.sh**: Skipped in quick validation mode
- **validate-lmstudio-backend.sh**: LM Studio is online; integration validation executed.
- **validate-plan-queues.sh**: Skipped in quick validation mode
- **validate-client-portal-local.sh**: Skipped in quick validation mode
- **validate-rag-local-multiclient.sh**: Skipped in quick validation mode
- **validate-local-billing.sh**: Skipped in quick validation mode
- **validate-observability-local.sh**: Skipped in quick validation mode
- validate-lmstudio-backend.sh exited with 1; see logs/validate-lmstudio-backend.sh.log

## Failures

- **validate-localhost-mode.sh**: exit code 1 (see `logs/validate-localhost-mode.sh.log`)
- **validate-status-local.sh**: exit code 1 (see `logs/validate-status-local.sh.log`)
- **validate-routing-local.sh**: exit code 1 (see `logs/validate-routing-local.sh.log`)
- **validate-local-docs.sh**: exit code 127 (see `logs/validate-local-docs.sh.log`)
- **check-feature-flags.sh**: exit code 1 (see `logs/check-feature-flags.sh.log`)

## Test Suite

- pytest exit code: `1`
- total: `0`
- passed: `0`
- failed: `0`
- errors: `0`
- skipped: `0`
- log: [view](logs/pytest.log)

## How to reproduce

```bash
./scripts/validators/validate-local-production-full.sh
```

## Useful commands

- Check logs: `ls -R /home/kleber/llm-inference-stack/scripts/artifacts/local-production-validation/20260609T214059/logs/`
- Tail all logs: `tail -f /home/kleber/llm-inference-stack/scripts/artifacts/local-production-validation/20260609T214059/logs/*.log`
- Check services: `docker compose ps`

## Out of scope

- Real PSP (Stripe/MercadoPago) integration tests.
- External DNS/SSL validation (handled by cloud provider).
- GPU stress testing (requires dedicated environment).

## Conclusion

Critical failures were detected. Please resolve them before proceeding to deployment.