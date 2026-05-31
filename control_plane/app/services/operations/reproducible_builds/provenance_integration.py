from typing import Any

from app.services.operations.reproducible_builds.hash_utils import sha256_hex


class ReproducibleBuildProvenanceIntegration:
    def integrate_with_phase80_provenance(self, manifest: Any) -> dict[str, Any]:
        payload = {
            "client_id": str(manifest.client_id),
            "build_manifest_id": manifest.id,
            "source_reference": manifest.source_reference,
            "phase80_alignment": "conceptual_only",
        }
        return {
            "integration_hash": sha256_hex({"kind": "phase80_provenance_alignment", **payload}),
            "phase": "phase80",
            "mode": "conceptual_only",
            "offline_compatible": True,
        }

    def integrate_with_sbom_placeholder(self, manifest: Any) -> dict[str, Any]:
        payload = {
            "client_id": str(manifest.client_id),
            "build_manifest_id": manifest.id,
            "build_scope": manifest.build_scope,
            "sbom_placeholder": True,
        }
        return {
            "sbom_placeholder_hash": sha256_hex({"kind": "phase80_sbom_placeholder_alignment", **payload}),
            "signature_only": True,
            "real_signing": False,
            "external_dependency_resolver": False,
        }

    def validate_supply_chain_alignment(self, manifest: Any) -> dict[str, Any]:
        aligned = manifest.replay_safe and manifest.reproducibility_status != "revoked"
        return {
            "aligned": aligned,
            "verification_status": "passed" if aligned else "warning",
            "deterministic_only": True,
            "notes": [
                "phase 80 provenance placeholder integration only",
                "no external dependency resolver",
                "no real cryptographic signing",
            ],
        }

    def explain_integration(self, manifest: Any) -> dict[str, Any]:
        return {
            "build_manifest_id": manifest.id,
            "integration_scope": "provenance_and_sbom_placeholder",
            "notes": [
                "integration conceptual with Phase 80 provenance/SBOM placeholder",
                "no formal certification of reproducibility",
                "offline-first deterministic verification only",
            ],
        }
