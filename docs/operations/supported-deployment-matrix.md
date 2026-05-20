# Supported Deployment Matrix

This document defines the supported deployment configurations, hardware limits, and system software prerequisites for the `llm-inference-stack` platform.

## Supported Operating Systems

| OS Family | Distribution | Versions | Architecture | Support Level |
| --- | --- | --- | --- | --- |
| **Linux (Debian)** | Ubuntu Server | 22.04 LTS, 24.04 LTS | x86_64 | **Supported** (Primary) |
| **Linux (RedHat)** | RHEL / Rocky Linux | 9.x | x86_64 | **Supported** |
| **macOS** | macOS (Darwin) | 13.x+ (Ventura+) | Apple Silicon (M1/M2/M3) | **Advisory** (Local Dev only) |

---

## Container and Language Runtimes

| Runtime | Minimum Version | Recommended Version | Purpose |
| --- | --- | --- | --- |
| **Docker Engine** | `24.0.0` | `26.x.x` | Container runtime engine |
| **Docker Compose** | `2.20.0` | `2.26.x` | Orchestration interface |
| **Python** | `3.10` | `3.12.x` | Local automation, host dependencies |
| **PostgreSQL** | `15.0` | `16.x` | Platform metadata database |

---

## Hardware and Resource Limits (Local Appliance Mode)

### CPU Only Mode
- **VCPUs**: Minimum 4 cores, Recommended 8+ cores.
- **RAM**: Minimum 16 GB, Recommended 32 GB.
- **Disk Space**: Minimum 20 GB free space (excludes models storage).

### GPU Accelerated Mode
- **NVIDIA GPU**: CUDA Compute Capability 8.0+ (Ampere, Ada Lovelace, Hopper).
- **VRAM**: Minimum 16 GB VRAM (e.g. RTX 4080, L4, A10G), Recommended 24 GB+ VRAM.
- **NVIDIA Driver**: `535.x.x` or newer.
- **NVIDIA Container Toolkit**: Required for Docker GPU passthrough.
