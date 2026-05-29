# Firecracker MicroVM Isolation

Firecracker uses KVM to launch lightweight MicroVMs in sub-second times, providing virtual machine level isolation for serverless workloads.

## Usage
Enabled via `AGENT_CODE_SANDBOX_FIRECRACKER_ENABLED=true`.

## Security
When `AGENT_CODE_SANDBOX_MICROVM_REQUIRED` is enabled, the platform ensures that code is executed inside a MicroVM, preventing container escape attacks from reaching the host kernel.
