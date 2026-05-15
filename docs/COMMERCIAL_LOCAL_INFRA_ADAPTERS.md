# Commercial Local Infra Adapters (Phase 23)

This phase adds opt-in support for local infrastructure management, specifically for Proxmox VE and local GPU nodes.

## Security Model

- **Opt-in Only**: All adapters are disabled by default.
- **Dry-run by Default**: Even when enabled, adapters default to `dry_run=true`.
- **Allowlists**: Destructive actions on Proxmox require VM/CT IDs to be in an explicit allowlist.
- **Sanitization**: Proxmox tokens and sensitive GPU process details are sanitized from logs and API responses.
- **Restricted GPU Actions**: Potentially dangerous actions (power limits, process killing, service restarts) are blocked by default.

## Proxmox Adapter

Allows controlling Proxmox VMs and Containers via the PVE API.

### Configuration

```env
COMMERCIAL_PROXMOX_EXECUTION_ENABLED=true
COMMERCIAL_PROXMOX_API_URL=https://pve.example.local:8006
COMMERCIAL_PROXMOX_NODE=pve-node-01
COMMERCIAL_PROXMOX_TOKEN_ID=user@pve!tokenid
COMMERCIAL_PROXMOX_TOKEN_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
COMMERCIAL_PROXMOX_VERIFY_TLS=true
COMMERCIAL_PROXMOX_DRY_RUN=true
COMMERCIAL_PROXMOX_ALLOWED_VM_IDS=100,101,102
COMMERCIAL_PROXMOX_ALLOWED_CT_IDS=200,201
```

### Supported Actions

- `start_vm`: Starts the VM/CT.
- `stop_vm`: Stops the VM/CT (Requires approval).
- `restart_vm`: Reboots the VM/CT (Requires approval).
- `inspect_vm`: Returns current status.

## Local GPU Adapter

Manages and monitors local GPUs using `nvidia-smi`.

### Configuration

```env
COMMERCIAL_LOCAL_GPU_EXECUTION_ENABLED=true
COMMERCIAL_LOCAL_GPU_DRY_RUN=true
COMMERCIAL_LOCAL_GPU_ALLOWED_ACTIONS=inspect,metrics
COMMERCIAL_LOCAL_GPU_ALLOW_POWER_LIMIT=false
COMMERCIAL_LOCAL_GPU_ALLOW_PROCESS_KILL=false
COMMERCIAL_LOCAL_GPU_ALLOW_SERVICE_RESTART=false
```

### Supported Actions

- `inspect`: Lists GPUs.
- `metrics`: Collects utilization, memory, temperature, and power draw.
- `power_limit`: Sets power limit in Watts (Disabled by default).
- `kill_process`: Kills a GPU process by PID (Strictly blocked in this phase).
- `service_restart`: Restarts the local inference service (Disabled by default).

## Admin Endpoints

- `GET /admin/routing/infra/local-gpu/metrics`: Returns detailed GPU metrics.
- `GET /admin/routing/infra/proxmox/capacity`: Returns Proxmox node capacity (CPU/RAM).

## Risks

- **Execution Safety**: Real execution can impact production workloads. Always use `dry_run` first.
- **API Availability**: If Proxmox API is down, status checks will fail gracefully but may delay automated recovery.
- **GPU Throttling**: Power limit changes can impact performance.
