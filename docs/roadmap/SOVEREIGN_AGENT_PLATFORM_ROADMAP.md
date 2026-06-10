---
owner: platform-ops
status: proposed
---

# Sovereign Agent Platform Roadmap

## Purpose

This roadmap decomposes the `v2.1.0-sovereign-agent-platform` line into incremental delivery phases. It uses enterprise planning language and explicitly marks foundation or advisory capabilities where operational maturity is still being built.

## Planning Assumptions

- All listed capabilities are opt-in until phase validation is complete.
- "Probable files" indicate likely delivery surfaces, not a promise that every file will change.
- "Acceptance" means internal release readiness, not external certification.
- Trust, attestation, confidential runtime, and ISO-related items remain environment-dependent.

## Phase 1: 30-60 days

### Delivery intent

Land the sovereign runtime foundation: routing, local high-throughput inference backends, multimodal execution, replay/memory discipline, operator CLI, and IDE integration baseline.

| Item | Objective | Probable files | Feature flag | Risk | Acceptance criteria | Expected tests |
|------|-----------|----------------|--------------|------|---------------------|----------------|
| Multi-backend inference router v2 | Introduce backend arbitration across local/API inference targets with auditable decisions. | `control_plane/app/api/admin_inference.py`, `control_plane/app/services/inference_proxy.py`, `control_plane/app/models/inference_backend.py`, `control_plane/app/contracts/provider.py` | `SOVEREIGN_ROUTER_V2_ENABLED` | Provider drift and routing regressions can silently change cost/latency posture. | Decisions are deterministic enough for audit, tenant policy filters apply before backend selection, and fallback stays explicit. | Router unit tests, provider contract tests, routing regression suite. |
| vLLM/TGI | Add a normalized adapter path for vLLM and TGI serving targets. | `control_plane/app/api/providers.py`, `control_plane/app/services/providers/local_provider.py`, `control_plane/app/services/providers/registry.py`, `docs/inference/vllm-backend.md`, `docs/operations/vllm-deployment.md` | `SOVEREIGN_VLLM_TGI_ENABLED` | Backend protocol differences may break streaming, token accounting, or model metadata. | Both backends register with consistent health/state metadata and support guarded streaming validation. | `tests/test_vllm.py`, provider streaming tests, readiness smoke tests. |
| Vision/multimodal | Expand the multimodal plane for image/document workflows under governance. | `control_plane/app/api/multimodal.py`, `control_plane/app/api/multimodal_v2.py`, `control_plane/app/services/multimodal/`, `control_plane/app/models/multimodal.py`, `docs/multimodal/` | `SOVEREIGN_MULTIMODAL_FOUNDATION_ENABLED` | Asset persistence and moderation gaps can create sovereignty or privacy issues. | Tenant isolation, retention controls, and capability-based routing are enforced for multimodal requests. | `tests/test_multimodal.py`, `tests/test_multimodal_v2.py`, multimodal harness tests. |
| Agent memory hierarchy | Standardize memory levels and lifecycle controls for agent execution. | `control_plane/app/api/agent_memory_admin.py`, `control_plane/app/api/agent_cognitive_memory_admin.py`, `control_plane/app/models/advanced_memory.py`, `control_plane/app/models/agent_federated_memory.py`, `sdk/python/kleberai/memory.py` | `SOVEREIGN_MEMORY_HIERARCHY_ENABLED` | Memory poisoning, retention sprawl, and retrieval inconsistency can erode determinism. | Working, episodic, semantic, and federated modes are explicit, policy-aware, and replay-referenceable. | `tests/test_agent_memory.py`, `tests/test_advanced_memory.py`, `tests/test_federated_memory.py`, `tests/test_memory_erasure.py`. |
| Deterministic replay | Consolidate replay for agents, workflows, and checkpoints as a release-grade diagnostic surface. | `control_plane/app/services/deterministic_execution/`, `control_plane/app/models/deterministic_execution.py`, `control_plane/app/services/runtime/determinism_repair.py`, `docs/agents/replay.md` | `SOVEREIGN_DETERMINISTIC_REPLAY_ENABLED` | Replay may re-trigger side effects or diverge from recorded evidence. | Replay produces auditable reconstruction paths, blocks unsafe re-execution by default, and surfaces evidence gaps. | `tests/test_agent_replay.py`, `tests/test_replay_verification.py`, `tests/test_checkpoint_replay.py`, `tests/test_workflow_replay_sessions.py`. |
| Remote attestation advisory | Expose remote attestation readiness signals as advisory controls and evidence capture. | `control_plane/app/api/operations_attestation_admin.py`, `control_plane/app/api/commercial_attestation_public.py`, `control_plane/app/models/operations/attestation_framework.py`, `control_plane/app/contracts/attestation.py`, `docs/security/attestation.md` | `SOVEREIGN_REMOTE_ATTESTATION_ADVISORY_ENABLED` | Operators may mistake evidence collection for formal assurance. | All surfaces label the feature advisory/foundational; evidence and receipts are exportable for internal review only. | `tests/e2e/test_attestation_plugin_flow.py`, `tests/integration/operations/test_attestation_replay_verifier.py`, attestation API tests. |
| `agentctl` CLI | Make sovereign workflows operable from the CLI for provisioning, validation, and promotion tasks. | `scripts/agentctl`, `scripts/dev/agentctl_pkg/main.py`, `scripts/dev/agentctl_pkg/utils.py`, `docs/cli/agentctl.md` | `SOVEREIGN_AGENTCTL_V2_ENABLED` | CLI/API mismatch can cause broken automation or misleading operator output. | Commands cover release-relevant workflows with stable exit codes and machine-readable output where needed. | `tests/test_agentctl.py`, CLI smoke tests, docs command examples review. |
| VS Code plugin foundation | Establish a supported extension skeleton for local control-plane interaction. | `integrations/vscode-extension/package.json`, `integrations/vscode-extension/src/extension.ts`, `integrations/vscode-extension/README.md` | `SOVEREIGN_VSCODE_FOUNDATION_ENABLED` | Foundation scope can be misread as full IDE product commitment. | Authentication, health, and basic control-plane actions work; extension is clearly marked as foundation scope. | Extension packaging checks, command smoke tests, contract tests against core API. |

## Phase 2: medium term

### Delivery intent

Open interoperability and distribution surfaces carefully: protocols, evaluation, marketplace governance, federation, appliance packaging, air-gap transport, and policy portability.

| Item | Objective | Probable files | Feature flag | Risk | Acceptance criteria | Expected tests |
|------|-----------|----------------|--------------|------|---------------------|----------------|
| MCP/A2A | Expand protocol interoperability across tools and peer agents. | `control_plane/app/api/agent_mcp_admin.py`, `control_plane/app/api/agent_a2a.py`, `control_plane/app/api/a2a_router.py`, `control_plane/app/models/agent_mcp_registry.py`, `control_plane/app/models/agent_mcp_oauth.py`, `docs/agents/mcp.md` | `SOVEREIGN_MCP_A2A_ENABLED` | Protocols widen the attack surface and can blur approval boundaries. | Registration, auth, replay visibility, and policy enforcement exist for tool and agent calls. | MCP/A2A API tests, delegated auth tests, contract validation. |
| Evaluation Arena | Create a formal evaluation comparison surface for models, prompts, and routers. | `control_plane/app/api/admin_evaluation.py`, `control_plane/app/services/evaluation/`, `control_plane/app/models/evaluation.py`, `control_plane/app/services/mlops/evaluation_artifacts.py`, `docs/agents/evals.md` | `SOVEREIGN_EVAL_ARENA_ENABLED` | Weak dataset controls can make results non-repeatable or non-defensible. | Eval runs are versioned, reproducible enough for internal comparison, and separated from promotion decisions unless explicitly linked. | `tests/test_evaluation_arena.py`, eval artifact tests, score regression tests. |
| Marketplace | Strengthen governed publication for agents/plugins and sovereign bundles. | `control_plane/app/api/admin_marketplace.py`, `control_plane/app/api/agent_marketplace_admin.py`, `control_plane/app/api/plugin_marketplace_admin.py`, `control_plane/app/models/agent_marketplace.py`, `control_plane/app/models/plugins/marketplace.py`, `docs/plugins/marketplace.md` | `SOVEREIGN_MARKETPLACE_ENABLED` | Publication without robust review or signatures creates supply-chain risk. | Submit/review/publish flow is gated, reviewable, and signature-aware; default posture remains private/internal-first. | `tests/test_agent_marketplace.py`, `tests/control_plane/test_plugin_marketplace.py`, signature and review workflow tests. |
| Federation mesh | Advance from sync primitives to bounded sovereign mesh behavior. | `control_plane/app/api/admin_federation_mesh.py`, `control_plane/app/api/commercial_federation_admin.py`, `control_plane/app/services/federation/mesh/`, `control_plane/app/models/federation_mesh.py`, `control_plane/app/domains/federation/` | `SOVEREIGN_FEDERATION_MESH_ENABLED` | Cross-site inconsistency can damage trust, lineage, and policy coherence. | Mesh enrollment, compatibility negotiation, and replay-verifiable receipts are available behind explicit peer trust setup. | Federation mesh tests, `tests/integration/operations/test_federation_replay_verifier.py`, compatibility tests. |
| Appliance mode | Provide a repeatable appliance-style deployment profile for sovereign environments. | `control_plane/app/api/commercial_appliance_admin.py`, `control_plane/app/models/commercial_appliance.py`, `docs/LOCAL_APPLIANCE_MODE.md`, `docs/LOCAL_AI_APPLIANCE_BRANDING.md` | `SOVEREIGN_APPLIANCE_MODE_ENABLED` | Appliance packaging can mask operational prerequisites or increase support burden. | Profile assumptions, hardware/software bounds, backup/restore steps, and recovery flows are documented and testable. | Appliance API tests, install profile smoke tests, restore validation. |
| Air-gapped updates | Add offline bundle import/export, verification, and staged promotion. | `control_plane/app/services/governance/airgap_sync.py`, `control_plane/app/services/managed_control_plane/managed_policy_sync.py`, `docs/SOVEREIGN_AIRGAP_GOVERNANCE.md`, `docs/UPGRADE_ROLLBACK_LOCAL.md`, `docs/RELEASE_BUNDLE_LOCAL.md` | `SOVEREIGN_AIRGAP_UPDATES_ENABLED` | Unsigned bundles or unclear rollback can break sovereign trust expectations. | Update bundles are verifiable, transport-friendly, and recoverable with operator-visible audit logs. | Bundle verification tests, import/export tests, rollback drill scripts. |
| Policy Engine OPA/Cedar-ready | Prepare the governance plane for multi-dialect policy authoring. | `control_plane/app/api/governance_policy_engine_admin.py`, `control_plane/app/services/governance/policy_engine/`, `control_plane/app/models/governance/policy_engine.py`, `docs/OPA_REGO_POLICY_RUNTIME.md`, `docs/POLICY_GOVERNANCE.md` | `SOVEREIGN_POLICY_ENGINE_MULTI_DIALECT_ENABLED` | Abstracting policy dialects can hide non-equivalent semantics. | The platform can ingest and compare policy bundles with clear unsupported-surface warnings and advisory evaluation paths. | Policy evaluator tests, policy replay tests, schema/contract tests. |

## Phase 3: long term

### Delivery intent

Push deeper sovereignty and efficiency themes only after runtime, policy, and distribution foundations are stable.

| Item | Objective | Probable files | Feature flag | Risk | Acceptance criteria | Expected tests |
|------|-----------|----------------|--------------|------|---------------------|----------------|
| Confidential Computing | Extend confidential runtime foundations where supported infrastructure exists. | `control_plane/app/api/commercial_confidential_runtime_admin.py`, `control_plane/app.models.commercial.commercial_confidential_runtime.py`, `docs/CONFIDENTIAL_RUNTIME.md`, `docs/security/real_crypto_readiness.md` | `SOVEREIGN_CONFIDENTIAL_COMPUTE_ADVISORY_ENABLED` | The largest risk is overstating real-world assurance across heterogeneous environments. | Capability remains advisory/foundation until environment probes, evidence, and operator docs are complete. | `tests/test_confidential_runtime.py`, `tests/test_confidential_runtime_enforcement.py`, confidential export/logging tests. |
| ISO bootable | Offer a bootable delivery vehicle for appliance-style sovereign installs. | `docs/CUSTOMER_INSTALL_WIZARD.md`, `docs/CUSTOMER_INSTALL_GUIDE.md`, `docs/FRESH_MACHINE_VALIDATION.md`, release build scripts under `scripts/` or packaging workflows | `SOVEREIGN_BOOTABLE_ISO_ENABLED` | Build reproducibility, firmware variance, and recovery flows are difficult to stabilize. | Boot media is internally reproducible enough for validation, with documented install/repair workflow and rollback media. | Image build checks, first-boot smoke tests, recovery validation. |
| Full reproducible sovereign stack | Make build, packaging, and artifact verification end-to-end and operator-auditable. | `docs/RELEASE_ARTIFACTS_SECURITY.md`, `docs/operations/reproducible_build_artifact_verification.md`, `docs/releases/sbom.md`, `scripts/validators/check-secrets.sh` | `SOVEREIGN_REPRODUCIBLE_STACK_ENABLED` | Non-hermetic dependencies can break the trust chain invisibly. | Provenance, SBOM, and verification steps cover the stack with explicit exceptions rather than implicit gaps. | Reproducible-build validation, SBOM tests, artifact replay verification tests. |
| Advanced GPU scheduling | Add richer placement and fairness behavior for heterogeneous cluster topologies. | `control_plane/app/services/gpu_orchestrator.py`, `control_plane/app/api/gpu_autoscaling_admin.py`, `control_plane/app/models/runtime/gpu_orchestration.py`, `docs/runtime/gpu-orchestration.md` | `SOVEREIGN_ADVANCED_GPU_SCHEDULING_ENABLED` | Placement heuristics can reduce fairness or cause performance instability. | Scheduler decisions are observable, policy-bounded, and introduced as advisory planning before strong automation. | GPU scheduler tests, autoscaling tests, placement regression benchmarks. |
| Distillation/pruning pipeline | Add controlled optimization workflows for smaller sovereign deployment footprints. | `control_plane/app/services/mlops/`, evaluation artifacts, future optimization pipeline modules, `docs/MODEL_BENCHMARK_LOCAL.md` | `SOVEREIGN_MODEL_OPTIMIZATION_PIPELINE_ENABLED` | Model quality can regress without lineage, eval discipline, and promotion controls. | Optimization outputs include lineage, benchmark delta, and approval gates before routing into supported surfaces. | Pipeline tests, eval comparison tests, lineage/provenance tests. |

## Cross-phase dependencies

1. Router v2, replay, and memory hierarchy should land before Evaluation Arena is used for release gating.
2. Attestation advisory, air-gapped updates, and reproducible builds reinforce one another and should share artifact formats where possible.
3. Marketplace, federation mesh, and policy portability depend on explicit trust contracts and version negotiation.
4. Advanced GPU scheduling and distillation/pruning should not bypass replay, lineage, or evaluation controls established earlier.

## Validation model

- Phase 1 validation: routing, multimodal, memory, replay, CLI, and advisory attestation smoke plus regression coverage
- Phase 2 validation: protocol contracts, evaluation reproducibility, marketplace review, federation receipts, appliance recovery, and air-gap bundle verification
- Phase 3 validation: confidential runtime enforcement, boot/install reproducibility, stack provenance, GPU scheduler stability, and optimization lineage

## Related Documents

- [Release Plan: v2.1.0 Sovereign Agent Platform](../releases/V2_1_0_SOVEREIGN_AGENT_PLATFORM.md)
- [Documentation Index](../index.md)
