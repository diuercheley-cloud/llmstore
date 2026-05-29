---
owner: platform-ops
status: consolidated
---

# Data Boundaries and Privacy

## Principles
The Managed Control Plane is designed to manage remote installations without exfiltrating sensitive customer data.

## Shared Data (Control Plane ← Appliance)
The following information is synchronized periodically:
- **Version**: Current software version of the appliance.
- **Health**: Overall health status (Healthy, Degraded, Critical).
- **Readiness**: Boolean indicating if the appliance is ready to serve requests.
- **Capacity Summary**: Aggregate metrics on GPU/CPU availability.
- **Enabled Providers**: List of providers (e.g., Ollama, LMStudio) currently enabled.
- **Available Models**: List of models registered on the appliance.

## Protected Data (STAYS ON APPLIANCE)
The following data **NEVER** leaves the local appliance:
- **Prompts and Completions**: All inference data is local.
- **API Keys and Secrets**: Provider credentials and client keys are stored locally.
- **Documents**: RAG uploads and chunks remain in the local vector database.
- **Audit Logs**: Detailed governance and security logs are kept on-premise.

## Multi-tenancy Isolation
- **Organization Level**: Data is strictly partitioned by `organization_id`.
- **Workspace Level**: Resource management (like appliances) is partitioned by `workspace_id`.
