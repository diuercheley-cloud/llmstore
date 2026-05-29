---
owner: platform-ops
status: consolidated
---

# Architecture Overview (Customer Edition)

## High-Level Diagram
The stack consists of a centralized **Control Plane** for management and distributed **Data Planes** for local inference.

## Key Components
1. **Control Plane:** Web UI, API, Database, Policy Engine.
2. **Data Plane:** Model Host (vLLM/Triton), Router, Local Cache.
3. **PKI Infrastructure:** Manages identity and encryption certificates.

## Data Flow
1. Client sends request to Data Plane.
2. Data Plane checks auth/policy with Control Plane (or local cache).
3. Data Plane performs inference.
4. Telemetry is sent back to Control Plane.

## Connectivity Requirements
- Ports 443 (HTTPS) and 6443 (mTLS) are standard.
- Low latency between Control and Data planes is recommended but not required.
