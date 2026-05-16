from app.services.operations.reproducible_builds.provenance_integration import ReproducibleBuildProvenanceIntegration
from app.services.operations.reproducible_builds.reproducible_build_service import ReproducibleBuildService


def test_phase80_provenance_integration():
    manifest = ReproducibleBuildService().create_build_manifest(
        {
            "client_id": "tenant-a",
            "build_name": "plugin-build",
            "build_scope": "plugin",
            "source_reference": "plugins/example",
            "deterministic_version": "v1",
            "build_environment_hash": "a" * 64,
            "replay_safe": True,
        }
    )
    integration = ReproducibleBuildProvenanceIntegration()
    assert integration.integrate_with_phase80_provenance(manifest)["phase"] == "phase80"
    assert integration.integrate_with_sbom_placeholder(manifest)["placeholder_only"] is True
    assert integration.validate_supply_chain_alignment(manifest)["aligned"] is True
