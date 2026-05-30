# E2E

## Priority Flows

- Agent Executor real flow: PASS via `tests/e2e/test_agent_executor_real_flow.py`.
- Google A2A protocol flow: PASS via `tests/e2e/test_agent_a2a_protocol.py`.
- WebSocket streaming flow: PASS via `tests/e2e/test_agent_websocket_streaming.py`.
- Production agentic E2E suite: PASS via `make production-agentic-e2e`.

## Observations

- The executor flow initially failed because semantic memory indexing referenced a missing runtime setting; restoring `AGENT_MEMORY_EMBEDDINGS_PROVIDER` fixed the completion path.
- The A2A and WebSocket flows passed without additional code changes once executed under the correct `PYTHONPATH`.
