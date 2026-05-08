# Local Production Validation Summary

**Result: SUCCESS**

## Metadata

- **Version:** v1.5.1-local-production
- **Branch:** feature/local-production-v1.5-hardening-plus
- **Commit:** a5f3596e68dae60228b442ad513d7a80d0429a2c
- **Base URL:** http://localhost:18080
- **Start Time:** 2026-05-08T19:33:20Z
- **End Time:** 2026-05-08T19:37:02Z
- **Total Duration:** 222s

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
| `validate-localhost-mode.sh` | OK | Yes | 0s | [view](logs/validate-localhost-mode.sh.log) |
| `validate-status-local.sh` | OK | Yes | 7s | [view](logs/validate-status-local.sh.log) |
| `validate-admin-lab-local.sh` | OK | Yes | 41s | [view](logs/validate-admin-lab-local.sh.log) |
| `validate-lmstudio-backend.sh` | OK | No | 7s | [view](logs/validate-lmstudio-backend.sh.log) |
| `validate-routing-local.sh` | OK | Yes | 0s | [view](logs/validate-routing-local.sh.log) |
| `validate-plan-queues.sh` | OK | Yes | 25s | [view](logs/validate-plan-queues.sh.log) |
| `validate-client-portal-local.sh` | OK | Yes | 0s | [view](logs/validate-client-portal-local.sh.log) |
| `validate-api-keys-local.sh` | OK | Yes | 0s | [view](logs/validate-api-keys-local.sh.log) |
| `validate-rag-local-multiclient.sh` | OK | Yes | 3s | [view](logs/validate-rag-local-multiclient.sh.log) |
| `validate-local-billing.sh` | OK | Yes | 0s | [view](logs/validate-local-billing.sh.log) |
| `validate-local-docs.sh` | OK | Yes | 0s | [view](logs/validate-local-docs.sh.log) |
| `validate-observability-local.sh` | OK | Yes | 56s | [view](logs/validate-observability-local.sh.log) |

## Test Suite

- pytest exit code: `0`
- total: `249`
- passed: `249`
- failed: `0`
- errors: `0`
- skipped: `0`
- log: [view](logs/pytest.log)

## How to reproduce

```bash
./scripts/validate-local-production-full.sh
```

## Useful commands

- Check logs: `ls -R /home/kleber/llm-inference-stack/artifacts/local-production-validation/20260508T163320/logs/`
- Tail all logs: `tail -f /home/kleber/llm-inference-stack/artifacts/local-production-validation/20260508T163320/logs/*.log`
- Check services: `docker compose ps`

## Out of scope

- Real PSP (Stripe/MercadoPago) integration tests.
- External DNS/SSL validation (handled by cloud provider).
- GPU stress testing (requires dedicated environment).

## Conclusion

The local production environment is healthy and ready for staging deployment.
