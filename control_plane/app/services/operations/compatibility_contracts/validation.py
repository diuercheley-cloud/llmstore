from typing import Any

from app.services.operations.compatibility_contracts.semantic_versioning import SemanticVersioningService


SEMVER = SemanticVersioningService()


def validate_schema_compatibility(source_schema_version: str, target_schema_version: str) -> dict[str, Any]:
    comparison = SEMVER.compare_versions(source_schema_version, target_schema_version)
    compatible = comparison["same_major"]
    if not compatible:
        status = "failed"
    elif comparison["same_minor"]:
        status = "passed"
    else:
        status = "warning"
    return {
        "status": status,
        "compatible": compatible,
        "summary": SEMVER.explain_version_comparison(comparison),
    }
