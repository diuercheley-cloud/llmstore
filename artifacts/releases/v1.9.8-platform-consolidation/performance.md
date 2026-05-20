# Performance: v1.9.8-platform-consolidation

Source: `artifacts/performance/latest/baseline.md`

## Measurements

- FastAPI startup probe: `FAILED` in the baseline script timeout window
- `import app.main`: `6.94s`
- `/health`: `2.440000ms`
- `/ready`: `3.104000ms`
- `/metrics`: `5.250000ms`

## Interpretation

- Endpoint latency remained low for the baseline host.
- Import time was captured successfully and can be used as a future regression reference.
- The startup probe needs hardening; the script timed out while waiting for the startup completion signal, so startup optimization claims should be treated as directional until this measurement is stabilized in CI.
