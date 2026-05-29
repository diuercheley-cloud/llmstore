---
owner: platform-ops
status: consolidated
---

# LLM Inference Stack — Documentation Index

> *Sovereign, offline-first, deterministic AI inference platform*

## Architecture

| Document | Description |
|----------|-------------|
| [Platform Overview](architecture/platform_overview.md) | Architecture overview, principles, bounded contexts, validation |
| [Platform Domain Map](architecture/platform_domain_map.md) | Bounded context map with Mermaid diagram and module boundaries |
| [Platform Guarantees & Limitations](architecture/platform_guarantees_and_limitations.md) | Formal guarantees, explicit limitations, prohibited claims |
| [Platform Operational Model](architecture/platform_operational_model.md) | Offline-first operations, event architecture, governance model |
| [Platform Validation Workflows](architecture/platform_validation_workflows.md) | Smoke, full, documentation, and recovery validation workflows |
| [Platform Module Relationships](architecture/platform_module_relationships.md) | Module dependency graph and cross-cutting concerns |
| [Platform Glossary](architecture/platform_glossary.md) | Terminology reference: deterministic, replay-safe, lineage, etc. |
| [Platform Phase Timeline](architecture/platform_phase_timeline.md) | Phase 69–82 evolution with objectives and dependencies |
| [Platform Documentation Consolidation Summary](architecture/platform_documentation_consolidation_summary.md) | Summary of this consolidation effort |
| [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md) | Original architecture overview |
| [SYSTEM_MAP.md](SYSTEM_MAP.md) | Module-to-source location mapping |
| [Bounded Contexts](architecture/bounded_contexts.md) | Official bounded context definitions |
| [Domain Contracts](architecture/domain_contracts.md) | Lightweight domain contracts for modularization |
| [Invariants](architecture/invariants.md) | Architectural invariants |
| [ADR Index](adr/README.md) | Architectural Decision Records |

## Governance

| Document | Description |
|----------|-------------|
| [Governance Documentation Foundation](governance/) | Governance documentation foundation |
| [Policy Governance](POLICY_GOVERNANCE.md) | Enterprise Policy Governance (Phase 34) |
| [Governance Federation](GOVERNANCE_FEDERATION.md) | Multi-region Governance Federation (Phase 35) |
| [Sovereign Airgap Governance](SOVEREIGN_AIRGAP_GOVERNANCE.md) | Sovereign airgap controls (Phase 37) |
| [Workflow Governance Enforcement](WORKFLOW_GOVERNANCE_ENFORCEMENT.md) | Workflow governance enforcement |
| [Claims Policy](compliance/claims_policy.md) | Prohibited claims policy |
| [OPA/Rego Policy Runtime](OPA_REGO_POLICY_RUNTIME.md) | Policy-as-code runtime |
| [Compliance Controls](COMMERCIAL_COMPLIANCE_CONTROLS.md) | Compliance controls |

## Federation

| Document | Description |
|----------|-------------|
| [Federation Sync Protocol](operations/sovereign_federation_synchronization_protocol.md) | Phase 77 federation sync |
| [Compatibility Contracts](operations/compatibility_contracts_and_version_negotiation.md) | Phase 78 compatibility |
| [Governance Federation](GOVERNANCE_FEDERATION.md) | Multi-region governance |
| [Distributed Control Plane Mesh](DISTRIBUTED_CONTROL_PLANE_MESH.md) | Phase 63 control plane mesh |
| [Federated Workflows](FEDERATED_DETERMINISTIC_WORKFLOWS.md) | Federated deterministic workflows |

## Plugin Runtime

| Document | Description |
|----------|-------------|
| [Formal Plugin ABI & Runtime](operations/formal_plugin_abi_extension_runtime.md) | Phase 79 plugin ABI |
| [Plugin Supply Chain & SBOM](operations/plugin_supply_chain_provenance_sbom.md) | Phase 80 supply chain |
| [Reproducible Builds](operations/reproducible_build_artifact_verification.md) | Phase 81 reproducible builds |
| [Adapter Sandbox](operations/adapter_sandbox.md) | Phase 73 adapter sandbox |
| [Signed Adapter Registry](operations/signed_adapter_registry.md) | Phase 74 signed registry |
| [Adapter Promotion Workflow](operations/adapter_promotion_workflow.md) | Phase 75 promotion workflow |

## Supply Chain

| Document | Description |
|----------|-------------|
| [Model Supply Chain](MODEL_SUPPLY_CHAIN.md) | Secure model supply chain (Phase 38) |
| [Runtime Model Integrity](RUNTIME_MODEL_INTEGRITY.md) | Runtime integrity monitor (Phase 39) |
| [Inference Reproducibility](INFERENCE_REPRODUCIBILITY.md) | Deterministic inference replay (Phase 40) |
| [Cryptographic Receipts](CRYPTOGRAPHIC_INFERENCE_RECEIPTS.md) | Signed inference receipts (Phase 41) |
| [Execution Proofs](VERIFIABLE_EXECUTION_PROOFS.md) | Verifiable AI execution proofs (Phase 60) |

## Reproducible Builds

| Document | Description |
|----------|-------------|
| [Reproducible Build Framework](operations/reproducible_build_artifact_verification.md) | Phase 81 framework |
| [Plugin Supply Chain](operations/plugin_supply_chain_provenance_sbom.md) | Plugin provenance and SBOM |
| [Release Artifacts Security](RELEASE_ARTIFACTS_SECURITY.md) | Release artifact security |

## Validation

| Document | Description |
|----------|-------------|
| [Validation Workflows](architecture/platform_validation_workflows.md) | Smoke, full, doc validation workflows |
| [Platform Architecture Validation](validation/) | Architecture validation suite |
| [Phase Index](PHASE_INDEX.md) | Historical phase progression |
| [Fresh Machine Validation](FRESH_MACHINE_VALIDATION.md) | Machine readiness check |
| [Local Production Validation](LOCAL_PRODUCTION_VALIDATION.md) | Production validation guide |

## Operations

| Document | Description |
|----------|-------------|
| [Platform Runbook](operations/platform_runbook.md) | Operations runbook |
| [Local Production Runbook](LOCAL_PRODUCTION_RUNBOOK.md) | Original production runbook |
| [Deterministic Event Architecture](operations/deterministic_event_architecture.md) | Event system (Phase 82) |
| [Operations Correlation](operations/operations_correlation_engine.md) | Phase 70 correlation |
| [Failure Forecasting](operations/phase_69_failure_forecasting_summary.md) | Phase 69 summary |
| [Remediation Planning](operations/remediation_planning.md) | Phase 71 planning |
| [Remediation Execution](operations/remediation_execution.md) | Phase 72 execution |
| [Operator Commands](OPERATOR_COMMANDS.md) | CLI reference |
| [Operator Error Codes](OPERATOR_ERROR_CODES.md) | Error code reference |

## Disaster Recovery

| Document | Description |
|----------|-------------|
| [Sovereign Disaster Recovery](operations/sovereign_disaster_recovery.md) | DR framework |
| [Disaster Recovery Local](DISASTER_RECOVERY_LOCAL.md) | Local DR guide |
| [Backup & Restore](UPGRADE_ROLLBACK_LOCAL.md) | Upgrade, rollback, restore |

## Security

| Document | Description |
|----------|-------------|
| [Security Local](SECURITY_LOCAL.md) | Security hardening |
| [Production Readiness](PRODUCTION_READINESS_LOCAL.md) | Production readiness |
| [Tenant Encryption](TENANT_ENCRYPTION_CONTROLS.md) | Phase 36 encryption |
| [Attestation Framework](operations/sovereign_execution_attestation_framework.md) | Phase 76 attestation |
| [Cryptographic Trust](CRYPTOGRAPHIC_TRUST_INFRASTRUCTURE.md) | Trust infrastructure |
| [Public Verifier](PUBLIC_VERIFIER.md) | Public verification CLI |
| [Trust Chain](TRUST_CHAIN.md) | Trust chain overview |
| [Hardware Attestation](HARDWARE_ATTESTATION_RUNTIME.md) | Hardware attestation runtime |

## RFCs

| Document | Description |
|----------|-------------|
| [RFC Index](rfc/) | RFC directory |

## Phase Summaries

| Document | Description |
|----------|-------------|
| [Phase 69 Summary](operations/phase_69_failure_forecasting_summary.md) | Predictive Failure Signals |
| [Phase 70 Summary](operations/phase_70_correlation_engine_summary.md) | Correlation Engine |
| [Phase 71 Summary](operations/phase_71_remediation_planning_summary.md) | Remediation Planning |
| [Phase 72 Summary](operations/phase_72_remediation_execution_summary.md) | Remediation Execution |
| [Phase 73 Summary](operations/phase_73_adapter_sandbox_summary.md) | Adapter Sandbox |
| [Phase 74 Summary](operations/phase_74_adapter_registry_summary.md) | Signed Adapter Registry |
| [Phase 75 Summary](operations/phase_75_adapter_promotion_summary.md) | Adapter Promotion |
| [Phase 76 Summary](operations/phase_76_attestation_framework_summary.md) | Attestation Framework |
| [Phase 77 Summary](operations/phase_77_federation_sync_summary.md) | Federation Sync |
| [Phase 78 Summary](operations/phase_78_compatibility_summary.md) | Compatibility Contracts |
| [Phase 79 Summary](operations/phase_79_plugin_runtime_summary.md) | Plugin ABI |
| [Phase 80 Summary](operations/phase_80_plugin_supply_chain_summary.md) | Plugin Supply Chain |
| [Phase 81 Summary](operations/phase_81_reproducible_build_summary.md) | Reproducible Builds |
| [Phase 82 Summary](operations/phase_82_platform_sustainability_summary.md) | Platform Sustainability |
