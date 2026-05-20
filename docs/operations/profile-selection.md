# Operations Guide: Runtime Profile Selection

This guide assists operators in choosing and applying the appropriate operational profiles for their deployment environment.

## Profiles Overview

### 1. Appliance Small (`appliance-small`)
- **Use Case**: Developer environments, single-node low-resource servers, local offline testing.
- **Key Characteristics**: Disables clustering (Kubernetes & distributed runtime), reduces queue size limits to conserve RAM, enables mock backends for testing without live GPUs.

### 2. Enterprise Edge (`enterprise-edge`)
- **Use Case**: On-premise corporate deployments, branch offices.
- **Key Characteristics**: Local model execution with full administrative security (RBAC), multi-tenancy, and observability features active.

### 3. Sovereign Cluster (`sovereign-cluster`)
- **Use Case**: High-security, air-gapped data centers.
- **Key Characteristics**: Multi-node distributed execution with strict boundaries. Disables outbound external APIs (e.g. OpenAI/Anthropic cloud routing) to guarantee absolute data privacy.

### 4. Managed Hybrid (`managed-hybrid`)
- **Use Case**: Cloud-connected enterprise deployments.
- **Key Characteristics**: Exchanges health heartbeat metadata with a managed central plane, allowing optional overflow/fallback routing to cloud providers.

### 5. Compliance Mode (`compliance-mode`)
- **Use Case**: Highly regulated environments (audits, health records, financial transactions).
- **Key Characteristics**: Enforces strict audit trails, advisory cryptographic controls, and mandates evidence logging.

---

## Applying Profiles via CLI

Operations can be executed using the integrated scripts:

### List available profiles
```bash
./scripts/runtime-profile-list.sh
```

### Validate configuration keys
```bash
./scripts/runtime-profile-validate.sh compliance-mode
```

### Dry-run Profile Application
This will output the configuration diff without modifying the server environment:
```bash
./scripts/runtime-profile-apply.sh compliance-mode
```

### Live Profile Application
To actually persist the changes to the server:
1. Ensure the environment variable `RUNTIME_PROFILE_APPLY_ENABLED=true` is set on the server process.
2. Run the apply script with the `--live` flag:
   ```bash
   ./scripts/runtime-profile-apply.sh --live compliance-mode
   ```

### Rollback
To undo the last profile application and restore the previous configuration:
```bash
./scripts/runtime-profile-apply.sh --live --rollback
```
