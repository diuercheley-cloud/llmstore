# Interoperability

## Cross-Surface Status

- A2A registration, signed message delivery, delegation policy checks, and audit generation: PASS.
- WebSocket streaming enforces tenant authentication, sanitizes payloads, and supports cancel/pause/resume commands: PASS.
- Feature-flag registry now recognizes the new interoperability surfaces (`AGENT_A2A_*`, `AGENT_WEBSOCKET_STREAMING_ENABLED`, assistants, batches, payment processing, token counting).

## Remaining Constraints

- The broader assistants, batches, payment processing, and token-counting surfaces are present in the worktree but were not the main blocker set for this release certification turn.
