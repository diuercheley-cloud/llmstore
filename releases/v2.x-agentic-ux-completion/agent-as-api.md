# Agent-as-API Deployment

## Status: IMPLEMENTED

## Components

- **API**: `control_plane/app/api/agent_deployments.py` - Agent deployment REST API
- **Models**: `control_plane/app/models/agent_deployments.py` - Deployment SQLAlchemy models
- **Services**: `control_plane/app/services/agent_deployments/` - Deployment orchestration
- **Facade**: `control_plane/app/services/agents/agent_api_facade.py` - Agent API facade for external access

## Key Features

- Deploy agents as standalone API endpoints
- Each deployed agent gets its own API route
- Runtime management (start, stop, scale deployments)
- Request routing to deployed agent instances
- Authentication and authorization for deployed agents
- Usage tracking and billing integration

## Feature Flag

`AGENT_AS_API_ENABLED` (experimental, owner: agent-platform)

## Documentation

- `docs/api/agent-as-api.md`
