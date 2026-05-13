# Local Production Validation Summary

**Result: SUCCESS**

## Metadata

- **Version:** v1.8.0-hybrid-ai-platform
- **Branch:** feature/v1.8.0-hybrid-ai-platform
- **Commit:** f73fbe77f3a37d29968f13e07e58991b9f4ed9e4
- **Base URL:** http://localhost:18080
- **Start Time:** 2026-05-13T16:07:05Z
- **End Time:** 2026-05-13T16:10:03Z
- **Total Duration:** 178s

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
| `validate-localhost-mode.sh` | OK | Yes | 7s | [view](logs/validate-localhost-mode.sh.log) |
| `validate-status-local.sh` | OK | Yes | 10s | [view](logs/validate-status-local.sh.log) |
| `validate-admin-lab-local.sh` | OK | Yes | 16s | [view](logs/validate-admin-lab-local.sh.log) |
| `validate-usable-chat-model-local.sh` | OK | Yes | 0s | [view](logs/validate-usable-chat-model-local.sh.log) |
| `validate-lmstudio-backend.sh` | OK | No | 6s | [view](logs/validate-lmstudio-backend.sh.log) |
| `validate-routing-local.sh` | OK | Yes | 4s | [view](logs/validate-routing-local.sh.log) |
| `validate-plan-queues.sh` | OK | Yes | 8s | [view](logs/validate-plan-queues.sh.log) |
| `validate-client-portal-local.sh` | OK | Yes | 5s | [view](logs/validate-client-portal-local.sh.log) |
| `validate-api-keys-local.sh` | OK | Yes | 7s | [view](logs/validate-api-keys-local.sh.log) |
| `validate-rag-local-multiclient.sh` | OK | Yes | 9s | [view](logs/validate-rag-local-multiclient.sh.log) |
| `validate-local-billing.sh` | OK | Yes | 9s | [view](logs/validate-local-billing.sh.log) |
| `validate-local-docs.sh` | OK | Yes | 2s | [view](logs/validate-local-docs.sh.log) |
| `validate-observability-local.sh` | OK | Yes | 12s | [view](logs/validate-observability-local.sh.log) |

## Test Suite

- pytest exit code: `0`
- total: `93`
- passed: `91`
- failed: `0`
- errors: `0`
- skipped: `2`
- log: [view](logs/pytest.log)

## How to reproduce

```bash
./scripts/validate-local-production-full.sh
```

## Useful commands

- Check logs: `ls -R /home/kleber/llm-inference-stack/artifacts/local-production-validation/20260513T130705/logs/`
- Tail all logs: `tail -f /home/kleber/llm-inference-stack/artifacts/local-production-validation/20260513T130705/logs/*.log`
- Check services: `docker compose ps`

## Out of scope

- Real PSP (Stripe/MercadoPago) integration tests.
- External DNS/SSL validation (handled by cloud provider).
- GPU stress testing (requires dedicated environment).

## Conclusion

The local production environment is healthy and ready for staging deployment.