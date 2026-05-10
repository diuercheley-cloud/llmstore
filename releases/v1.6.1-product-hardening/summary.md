# Local Production Validation Summary

**Result: SUCCESS**

## Metadata

- **Version:** v1.6.1-product-hardening
- **Branch:** feature/v1.6.1-product-hardening
- **Commit:** e485ec6027d84b621d1973d385989a37a256a72c
- **Base URL:** http://localhost:18080
- **Start Time:** 2026-05-10T20:52:00Z
- **End Time:** 2026-05-10T20:54:47Z
- **Total Duration:** 167s

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
| `validate-localhost-mode.sh` | OK | Yes | 9s | [view](logs/validate-localhost-mode.sh.log) |
| `validate-status-local.sh` | OK | Yes | 9s | [view](logs/validate-status-local.sh.log) |
| `validate-admin-lab-local.sh` | OK | Yes | 25s | [view](logs/validate-admin-lab-local.sh.log) |
| `validate-lmstudio-backend.sh` | OK | No | 7s | [view](logs/validate-lmstudio-backend.sh.log) |
| `validate-routing-local.sh` | OK | Yes | 3s | [view](logs/validate-routing-local.sh.log) |
| `validate-plan-queues.sh` | OK | Yes | 8s | [view](logs/validate-plan-queues.sh.log) |
| `validate-client-portal-local.sh` | OK | Yes | 7s | [view](logs/validate-client-portal-local.sh.log) |
| `validate-api-keys-local.sh` | OK | Yes | 6s | [view](logs/validate-api-keys-local.sh.log) |
| `validate-rag-local-multiclient.sh` | OK | Yes | 9s | [view](logs/validate-rag-local-multiclient.sh.log) |
| `validate-local-billing.sh` | OK | Yes | 7s | [view](logs/validate-local-billing.sh.log) |
| `validate-local-docs.sh` | OK | Yes | 1s | [view](logs/validate-local-docs.sh.log) |
| `validate-observability-local.sh` | OK | Yes | 15s | [view](logs/validate-observability-local.sh.log) |

## Test Suite

- pytest exit code: `0`
- total: `88`
- passed: `86`
- failed: `0`
- errors: `0`
- skipped: `2`
- log: [view](logs/pytest.log)

## How to reproduce

```bash
./scripts/validate-local-production-full.sh
```

## Useful commands

- Check logs: `ls -R /home/kleber/llm-inference-stack/artifacts/local-production-validation/20260510T175200/logs/`
- Tail all logs: `tail -f /home/kleber/llm-inference-stack/artifacts/local-production-validation/20260510T175200/logs/*.log`
- Check services: `docker compose ps`

## Out of scope

- Real PSP (Stripe/MercadoPago) integration tests.
- External DNS/SSL validation (handled by cloud provider).
- GPU stress testing (requires dedicated environment).

## Conclusion

The local production environment is healthy and ready for staging deployment.