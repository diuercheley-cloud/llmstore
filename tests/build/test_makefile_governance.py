from __future__ import annotations

from scripts import validate_makefile_governance as validator


def _recipe_for(parsed: validator.ParsedMakefile, target: str) -> str:
    definition = parsed.unique_targets[target]
    return "\n".join(definition.recipe_lines)


def test_duplicate_detection():
    parsed = validator.parse_makefile()
    assert validator.find_duplicate_targets(parsed) == []
    assert validator.find_duplicate_phony_entries(parsed) == []
    assert validator.find_shadowing_and_overrides(parsed) == []


def test_target_resolution():
    parsed = validator.parse_makefile()

    assert len(parsed.targets["measure-provider-costs-dry"]) == 1
    assert len(parsed.targets["measure-provider-costs"]) == 1
    assert len(parsed.targets["validate-policy-governance"]) == 1
    assert len(parsed.targets["validate-commercial-compliance-controls"]) == 1
    assert len(parsed.targets["validate-fake-data"]) == 1

    assert "./scripts/measure-real-provider-costs.sh --dry-run" in _recipe_for(parsed, "measure-provider-costs-dry")
    assert "./scripts/measure-real-provider-costs.sh --real" in _recipe_for(parsed, "measure-provider-costs")
    assert "./scripts/validate-policy-governance.sh" in _recipe_for(parsed, "validate-policy-governance")
    assert "validate-commercial-compliance-controls.sh" in _recipe_for(
        parsed, "validate-commercial-compliance-controls"
    )
    assert "validate-fake-demo-data.sh" in _recipe_for(parsed, "validate-fake-data")


def test_aggregate_ordering():
    parsed = validator.parse_makefile()

    assert parsed.variables["VALIDATE_PHASE_TARGETS"] == [
        "validate-phase-66-readiness",
        "validate-phase-69-failure-forecasting",
        "validate-phase-70-correlation-engine",
        "validate-phase-71-remediation-planning",
        "validate-phase-72-remediation-execution",
        "validate-phase-73-adapter-sandbox",
        "validate-phase-74-adapter-registry",
        "validate-phase-75-adapter-promotion",
        "validate-phase-76-attestation-framework",
        "validate-phase-77-federation-sync",
        "validate-phase-78-compatibility-contracts",
        "validate-phase-79-plugin-runtime",
        "validate-phase-80-plugin-supply-chain",
        "validate-phase-81-reproducible-builds",
        "validate-phase-82-platform-sustainability",
    ]
    assert parsed.variables["PLATFORM_VALIDATION_TARGETS"] == [
        "validate-architecture",
        "validate-governance",
        "validate-security",
    ]
    assert parsed.variables["ALL_VALIDATION_TARGETS"] == ["validate-platform"]


def test_legacy_alias_compatibility():
    parsed = validator.parse_makefile()

    legacy_aliases = {
        "first-run-local": "first-run",
        "first-run-demo": "first-run",
        "security-report": "security",
        "production-readiness": "readiness",
        "demo-local": "demo",
        "upgrade-local": "upgrade",
        "rollback-local": "rollback",
        "post-upgrade-smoke": "smoke",
        "benchmark-quick": "benchmark",
        "benchmark-model": "benchmark",
        "validate-local-production": "validate",
    }

    for alias, canonical in legacy_aliases.items():
        definition = parsed.unique_targets[alias]
        assert definition.is_alias
        assert definition.prerequisites == [canonical]


def test_validate_phase_reachability():
    parsed = validator.parse_makefile()
    edges = validator._aggregate_edges(parsed)

    seen: set[str] = set()

    def visit(target: str) -> None:
        if target in seen:
            return
        seen.add(target)
        for dependency in edges.get(target, []):
            visit(dependency)

    visit("validate-architecture")

    for phase_target in parsed.variables["VALIDATE_PHASE_TARGETS"]:
        assert phase_target in seen

    assert "validate-makefile-governance" in seen


def test_global_makefile_governance_validation():
    assert validator.validate() == []
