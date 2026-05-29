---
owner: platform-ops
status: consolidated
---

# Runtime Profiles Configuration

Runtime Profiles permit operators to quickly toggle and configure clusters using preset operation modes rather than modifying hundreds of discrete environment variables.

Profiles are located in `config/runtime-profiles/` as YAML files:
- `appliance-small.yaml`: Single-node edge installations.
- `enterprise-edge.yaml`: Local appliances with RBAC and full audit logs.
- `sovereign-cluster.yaml`: Distributed local multi-node configurations.
- `managed-hybrid.yaml`: Cloud-connected hybrid environments.
- `compliance-mode.yaml`: SOC 2 readiness enforced profile.

## Configuration Schema

Every profile file uses the following schema:

```yaml
profile_id: string       # Unique identifier (e.g. appliance-small)
name: string             # Human readable name
description: string      # Detailed purpose of the profile
settings:                # Dictionary of feature flags and configuration variables
  KEY_NAME: value
```

## Admin REST Endpoints

All actions require admin super-token header (`X-Admin-Token`):

### 1. List Available Profiles
- **URL**: `GET /admin/runtime-profiles`
- **Response**: List of YAML profile structures.

### 2. View Current Configuration
- **URL**: `GET /admin/runtime-profiles/current`
- **Response**: JSON mapping of active variables.

### 3. Validate Profile Settings
- **URL**: `POST /admin/runtime-profiles/validate`
- **Payload**: `{"profile_id": "appliance-small"}`
- **Response**: Checks keys against Pydantic settings schema.

### 4. Apply Profile / Rollback
- **URL**: `POST /admin/runtime-profiles/apply`
- **Payload**:
  ```json
  {
    "profile_id": "appliance-small",
    "dry_run": true,
    "rollback": false
  }
  ```
- **Response**: Returns the settings diff (`before` and `after`).
