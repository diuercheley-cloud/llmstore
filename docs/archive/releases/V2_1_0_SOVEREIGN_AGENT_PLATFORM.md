---
owner: platform-ops
status: proposed
---

# v2.1.0 Sovereign Agent Platform

## Objective

Evolve the platform toward a sovereign agent platform release line with incremental delivery, explicit operator gates, and advisory-first posture for capabilities that are still foundational.

## Release Positioning

- Release tag candidate: `v2.1.0-sovereign-agent-platform`
- Delivery model: incremental, phase-based, flag-gated
- Default posture: disabled by default for all new autonomous, federated, marketplace, confidential, and air-gap update surfaces
- Claims posture: readiness, foundation, advisory, or operator-preview unless validation gates and environment prerequisites are met
- Non-goal: no claim of formal certification, no claim of real confidential-computing assurance, and no claim of hardware-rooted attestation unless separately validated

## Rollout Principles

1. Preserve deterministic, replay-safe, offline-first defaults.
2. Land foundational contracts before operator-facing automation.
3. Treat new trust and sovereignty controls as advisory until evidence paths are stable.
4. Separate code presence from production claimability.
5. Require phase exit validation before expanding the supported surface.

## Phase Plan

### Phase 1: 30-60 days

Focus on core runtime expansion, multimodal execution, memory/replay hardening, operator CLI, and workstation integration foundations.

| Capability | Objective | Feature flag | Risk | Acceptance criteria | Expected tests |
|----------|-----------|--------------|------|---------------------|----------------|
| Multi-backend inference router v2 | Route per request across local, API, and sovereign backends with auditable backend decisions. | `SOVEREIGN_ROUTER_V2_ENABLED` | Regression in backend selection, latency inflation, fallback loops. | Backend choice is recorded, fail-closed behavior is preserved, tenant and policy constraints are enforced. | Router unit tests, policy-routing integration tests, latency/fallback regression tests. |
| vLLM/TGI | Standardize high-throughput local serving adapters for sovereign deployments. | `SOVEREIGN_VLLM_TGI_ENABLED` | Divergent token semantics, streaming incompatibility, capacity mis-sizing. | vLLM and TGI endpoints register through a common contract, stream correctly, and fail closed on incompatible models. | `tests/test_vllm.py`, provider contract tests, SSE compatibility tests. |
| Vision/multimodal | Expand governed image/document understanding in the existing multimodal plane. | `SOVEREIGN_MULTIMODAL_FOUNDATION_ENABLED` | Asset leakage, inconsistent moderation, storage growth. | Multimodal requests honor tenant boundaries, asset retention policy, and model capability checks. | `tests/test_multimodal.py`, `tests/test_multimodal_v2.py`, multimodal policy tests. |
| Agent memory hierarchy | Formalize working, episodic, semantic, and federated memory layering with isolation rules. | `SOVEREIGN_MEMORY_HIERARCHY_ENABLED` | Memory poisoning, retention drift, cross-tenant leakage. | Hierarchy selection is explicit per agent, isolation and TTL controls are enforceable, replay references remain stable. | `tests/test_agent_memory.py`, `tests/test_advanced_memory.py`, `tests/test_memory_erasure.py`, tenant isolation tests. |
| Deterministic replay | Strengthen replayability of agent and workflow execution for incident analysis and controlled promotion. | `SOVEREIGN_DETERMINISTIC_REPLAY_ENABLED` | Non-deterministic side effects, missing receipts, broken recovery paths. | Replay can reconstruct execution artifacts without hidden network dependence or unsafe re-execution. | `tests/test_agent_replay.py`, `tests/test_replay_verification.py`, `tests/test_workflow_replay_sessions.py`, `tests/test_checkpoint_replay.py`. |
| Remote attestation advisory | Provide advisory evidence capture and operator review flows for remote attestation readiness. | `SOVEREIGN_REMOTE_ATTESTATION_ADVISORY_ENABLED` | Overstated trust claims, incomplete evidence chain, operator confusion. | Documentation, API, and UI label the feature as advisory/foundational; evidence is auditable but not represented as formal assurance. | Attestation API tests, receipt validation tests, advisory-label docs review. |
| `agentctl` CLI | Expand the CLI into the operator control surface for sovereign runtime workflows. | `SOVEREIGN_AGENTCTL_V2_ENABLED` | Command drift, incomplete auth handling, broken automation scripts. | Core release workflows are scriptable from `agentctl` with stable output and explicit error codes. | `tests/test_agentctl.py`, CLI smoke tests, command output snapshot tests. |
| VS Code plugin foundation | Establish the extension contract for local developer/operator workflows without over-claiming GA readiness. | `SOVEREIGN_VSCODE_FOUNDATION_ENABLED` | Thin integration surface, version skew, accidental support expectations. | Extension can authenticate, call core APIs, and surface guarded status without implying full IDE governance coverage. | Extension smoke tests, package validation, API contract tests. |

### Phase 2: medium term

Focus on ecosystem interoperability, evaluation, distribution, federation, appliance operations, and policy portability.

| Capability | Objective | Feature flag | Risk | Acceptance criteria | Expected tests |
|----------|-----------|--------------|------|---------------------|----------------|
| MCP/A2A | Normalize tool and agent-to-agent interoperability under governed contracts. | `SOVEREIGN_MCP_A2A_ENABLED` | Trust boundary confusion, tool escalation, schema drift. | MCP and A2A endpoints are explicitly governed, authenticated, and replay-visible. | MCP admin/API tests, A2A contract tests, delegated auth tests. |
| Evaluation Arena | Compare models, agents, and routing strategies with auditable scoring and replayable datasets. | `SOVEREIGN_EVAL_ARENA_ENABLED` | Score instability, benchmark gaming, dataset contamination. | Arena runs are versioned, comparable, and tied to immutable eval inputs. | `tests/test_evaluation_arena.py`, eval artifact tests, score regression tests. |
| Marketplace | Mature the governed marketplace into a sovereign distribution surface with review gates. | `SOVEREIGN_MARKETPLACE_ENABLED` | Supply-chain abuse, metadata trust issues, unreviewed publication. | Submission, review, signature, and publication workflows remain operator-gated and auditable. | `tests/test_agent_marketplace.py`, plugin marketplace tests, signature workflow tests. |
| Federation mesh | Expand bounded cross-site coordination for sovereign environments. | `SOVEREIGN_FEDERATION_MESH_ENABLED` | Inconsistent policy sync, replay divergence, trust negotiation errors. | Mesh peers negotiate compatible versions, policy/data boundaries stay explicit, and sync receipts are available. | Federation sync tests, replay verifier tests, compatibility tests. |
| Appliance mode | Package a more opinionated sovereign deployment profile for controlled environments. | `SOVEREIGN_APPLIANCE_MODE_ENABLED` | Hidden dependencies, support sprawl, profile drift. | Appliance mode is profile-driven, documented, and recoverable with explicit operational constraints. | Appliance admin tests, profile validation, install/restore smoke tests. |
| Air-gapped updates | Introduce governed offline update bundles and staged import/export workflows. | `SOVEREIGN_AIRGAP_UPDATES_ENABLED` | Bundle tampering, version skew, failed rollback. | Offline bundles are signed or checksummed, import is auditable, and rollback path is documented. | Bundle validation tests, import/export tests, rollback drills. |
| Policy Engine OPA/Cedar-ready | Prepare the policy plane for multiple policy dialects without promising full parity on day one. | `SOVEREIGN_POLICY_ENGINE_MULTI_DIALECT_ENABLED` | Semantic mismatch, partial enforcement, operator misconfiguration. | Policy abstraction supports OPA/Cedar-ready contracts, advisory diffing, and explicit unsupported-surface warnings. | Policy evaluator tests, policy replay verifier tests, contract/schema tests. |

### Phase 3: long term

Focus on deeper sovereignty guarantees, reproducibility, hardware-aware scheduling, and model lifecycle optimization.

| Capability | Objective | Feature flag | Risk | Acceptance criteria | Expected tests |
|----------|-----------|--------------|------|---------------------|----------------|
| Confidential Computing | Build advisory foundations for protected execution profiles where hardware support exists. | `SOVEREIGN_CONFIDENTIAL_COMPUTE_ADVISORY_ENABLED` | Over-claiming security posture, environment variance, opaque failures. | The platform exposes advisory readiness signals, evidence capture, and fail-closed policy hooks without claiming universal assurance. | `tests/test_confidential_runtime.py`, `tests/test_confidential_runtime_enforcement.py`, export/logging control tests. |
| ISO bootable | Produce a bootable sovereign delivery path for controlled appliance deployment. | `SOVEREIGN_BOOTABLE_ISO_ENABLED` | Image drift, driver incompatibility, recovery complexity. | ISO artifacts are reproducible enough for internal validation, boot/install flow is documented, and rollback media exists. | Image build validation, installation smoke tests, recovery tests. |
| Full reproducible sovereign stack | Extend deterministic build and artifact verification across the full delivery chain. | `SOVEREIGN_REPRODUCIBLE_STACK_ENABLED` | Incomplete provenance chain, non-hermetic builds, evidence gaps. | Build inputs, artifacts, and verification steps are captured end to end with explicit exceptions documented. | Reproducible build tests, SBOM/provenance checks, artifact replay verification. |
| Advanced GPU scheduling | Improve placement, packing, and fairness controls for heterogeneous sovereign clusters. | `SOVEREIGN_ADVANCED_GPU_SCHEDULING_ENABLED` | Starvation, noisy-neighbor effects, poor device utilization. | Scheduler exposes advisory placement plans, bounded fairness controls, and observable decisions before automated enforcement. | GPU orchestration tests, autoscaling tests, scheduler regression tests. |
| Distillation/pruning pipeline | Add governed model optimization workflows for sovereign deployment footprints. | `SOVEREIGN_MODEL_OPTIMIZATION_PIPELINE_ENABLED` | Quality collapse, unverifiable datasets, lineage loss. | Optimization jobs produce lineage artifacts, evaluation deltas, and explicit promotion gates before deployment use. | Pipeline unit/integration tests, evaluation diff tests, artifact lineage tests. |

## Probable Delivery Areas

- Runtime and APIs: `control_plane/app/api/`, `control_plane/app/services/`, `control_plane/app/models/`
- Contracts and schemas: `control_plane/app/contracts/`, `control_plane/app/schemas/`, `control_plane/app/domains/`
- CLI and SDK: `scripts/agentctl`, `scripts/dev/agentctl.py`, `sdk/python/`, `sdk/node/`
- IDE integration: `integrations/vscode-extension/`
- Validation: `tests/`, `tests/control_plane/`, `scripts/validate-*.sh`
- Documentation and release artifacts: `docs/`, `artifacts/releases/`

## Release Risks

1. The release theme spans runtime, governance, federation, and tooling; scope pressure is the primary delivery risk.
2. Multimodal, memory, replay, and federation touch tenant isolation boundaries and require stronger regression coverage than feature count alone suggests.
3. Attestation and confidential computing language can become misleading unless consistently marked advisory and environment-dependent.
4. Marketplace and air-gap updates raise supply-chain expectations and should not move beyond gated preview without signed artifact verification.
5. Policy dialect expansion can create false equivalence between OPA and Cedar semantics if abstraction layers are underspecified.

## Validation Gates

Run before phase promotion:

```bash
make test
make validate-quick
make security
make operational-readiness
make platform-freeze-check
pytest tests/test_vllm.py tests/test_multimodal.py tests/test_multimodal_v2.py
pytest tests/test_agent_memory.py tests/test_advanced_memory.py tests/test_agent_replay.py
pytest tests/test_replay_verification.py tests/test_agentctl.py tests/test_evaluation_arena.py
pytest tests/test_agent_marketplace.py tests/test_confidential_runtime.py tests/test_confidential_runtime_enforcement.py
pytest tests/integration/operations/test_federation_replay_verifier.py tests/integration/operations/test_attestation_replay_verifier.py
```

## Phase Exit Criteria

### Exit criteria for Phase 1

1. Router v2, multimodal, memory hierarchy, deterministic replay, and `agentctl` changes are merged behind default-off flags.
2. Remote attestation language is advisory in code, docs, and operator-visible UI/API output.
3. VS Code integration is limited to foundation scope and clearly labeled as such.

### Exit criteria for Phase 2

1. Federation, marketplace, and air-gap update workflows produce auditable artifacts.
2. Evaluation Arena can compare runs without mutating production routing.
3. Policy portability remains readiness-oriented, not parity-claimed.

### Exit criteria for Phase 3

1. Confidential, ISO, reproducibility, GPU scheduling, and model optimization surfaces have environment prerequisites documented.
2. No long-term capability is represented as production-safe solely by unit-test presence.
3. The supported-surface matrix is updated before any production claim expansion.

## Expected Artifacts

- `artifacts/releases/v2.1.0-sovereign-agent-platform/summary.md`
- `artifacts/releases/v2.1.0-sovereign-agent-platform/validation.md`
- `artifacts/releases/v2.1.0-sovereign-agent-platform/risks.md`
- `artifacts/releases/v2.1.0-sovereign-agent-platform/feature-flags.md`
- `artifacts/releases/v2.1.0-sovereign-agent-platform/supported-surface.md`

## Related Documents

- [Sovereign Agent Platform Roadmap](../roadmap/SOVEREIGN_AGENT_PLATFORM_ROADMAP.md)
- [v2.1.0 Enterprise Agentic Autonomy](V2_1_0_AGENTIC_AUTONOMY.md)
- [Documentation Index](../index.md)
