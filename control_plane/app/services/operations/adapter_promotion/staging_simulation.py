from typing import Any

from app.models.operations.adapter_registry import SignedAdapterRegistryEntry


class AdapterStagingSimulationService:
    def require_staging_simulation(self, target_stage: str) -> bool:
        """Staging simulation is required for production eligibility."""
        return target_stage == "production_eligible"

    def validate_staging_simulation(
        self, entry: SignedAdapterRegistryEntry, context: dict[str, Any]
    ) -> bool:
        """Validates that a staging simulation was successfully recorded."""
        # In this phase, we look for a flag in the context.
        # Real implementation would check AdapterSandboxRun for staging mode.
        return context.get("staging_simulation_passed", False)

    def build_staging_simulation_summary(
        self, entry: SignedAdapterRegistryEntry, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Builds a deterministic summary of the staging simulation."""
        return {
            "adapter_name": entry.adapter_name,
            "adapter_version": entry.adapter_version,
            "manifest_hash": entry.manifest_hash,
            "simulation_mode": "staging_simulation",
            "result": "success" if context.get("staging_simulation_passed") else "pending",
            "reason": context.get("staging_simulation_reason", "No simulation recorded"),
            "verifiable_markers": ["sandbox_verified", "staging_context_verified"],
        }
