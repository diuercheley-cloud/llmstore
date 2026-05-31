# Sessões/Threads Persistentes

## Status: IMPLEMENTED

## Backend Components

- **API**: `control_plane/app/api/agent_sessions.py` - REST endpoints for session CRUD
- **Models**: `control_plane/app/models/agent_sessions.py` - SQLAlchemy session models
- **Services**: `control_plane/app/services/agents/sessions/` - Session management logic
- **Migration**: `control_plane/alembic/versions/20260530_0004_agent_sessions.py`

## Key Features

- Create, read, update, delete agent sessions
- Persist session state across agent invocations
- Session context carried through agent execution pipeline
- Integration with agent executor for session-aware routing

## Dependencies

- `AGENT_SESSIONS_ENABLED` feature flag
- Agent runtime must be enabled for session support
- Database migration required (Alembic)

## Tests

- `control_plane/tests/test_agent_sessions.py`

## Documentation

- `docs/agents/sessions-and-threads.md`
