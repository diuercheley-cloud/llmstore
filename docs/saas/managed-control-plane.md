---
owner: platform-ops
status: consolidated
---

# Managed Control Plane (SaaS Mode)

## Overview
The Managed Control Plane mode allows the `llm-inference-stack` to operate as a SaaS (Software as a Service) provider. In this mode, a central Control Plane can manage multiple remote appliances (installations) across different organizations and workspaces.

## Key Features
- **Multi-tenancy**: Isolation by Organization and Workspace.
- **Remote Management**: Centralized view of all enrolled appliances.
- **Status Sync**: Periodic heartbeats from appliances providing health, version, and capacity information.
- **Enrollment Flow**: Secure token-based enrollment for new appliances.

## Deployment Modes
- `appliance`: (Default) Standard on-premise/single-tenant mode.
- `managed_control_plane`: SaaS mode where the control plane manages remote appliances.
- `hybrid`: Managed mode with local inference capabilities enabled.

## Architecture
In `managed_control_plane` mode, the database includes tables for:
- `managed_organizations`
- `managed_workspaces`
- `managed_appliances`
- `appliance_enrollments`
- `appliance_heartbeats`

Remote appliances connect to the Managed Control Plane to register themselves and send periodic status updates.
