from app.services.operations.reproducible_builds.build_environment_policy import (
    BuildEnvironmentPolicyService,
)


def test_environment_policy_denies_external_network_and_resolution():
    service = BuildEnvironmentPolicyService()
    constraint = service.validate_environment_constraints(
        {
            "client_id": "tenant-a",
            "constraint_name": "offline-default",
            "constraint_scope": "plugin",
            "external_network_allowed": True,
            "external_dependency_resolution_allowed": True,
        }
    )
    offline = service.enforce_offline_constraints(constraint)
    assert offline["verification_status"] == "blocked"


def test_environment_policy_blocks_dynamic_installers():
    service = BuildEnvironmentPolicyService()
    constraint = service.validate_environment_constraints(
        {
            "client_id": "tenant-a",
            "constraint_name": "offline-default",
            "constraint_scope": "plugin",
        }
    )
    determinism = service.enforce_determinism_constraints(
        constraint, {"blocked_markers": ["dynamic dependency install"]}
    )
    assert determinism["verification_status"] == "blocked"
