import subprocess
import pytest
from pathlib import Path


def test_deprecated_surface_validation():
    """
    Ensures all deprecated surfaces have owners, replacements, and removal deadlines.
    Runs scripts/validate_deprecated_surface.py and asserts clean exit.
    """
    root_dir = Path(__file__).parent.parent.parent

    result = subprocess.run(
        ["python3", "scripts/validate_deprecated_surface.py"],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        pytest.fail(
            f"Deprecated surface validation failed:\n{result.stdout}"
        )


def test_deprecated_surface_inventory_exists():
    """
    Ensures the deprecated surface inventory file exists and has the AUTO-GENERATED header.
    """
    inventory_path = Path(__file__).parent.parent.parent / "docs/generated/deprecated_surface_inventory.md"
    assert inventory_path.exists(), (
        "docs/generated/deprecated_surface_inventory.md not found"
    )

    content = inventory_path.read_text(encoding="utf-8")
    assert "AUTO-GENERATED" in content, (
        "deprecated_surface_inventory.md missing AUTO-GENERATED header"
    )
    assert "# Deprecated Surface Inventory" in content, (
        "deprecated_surface_inventory.md missing title"
    )


def test_api_surface_deprecated_have_deadlines():
    """
    Ensures all api-surface.yaml deprecated entries have sunset_date or removal_date.
    """
    import yaml

    root_dir = Path(__file__).parent.parent.parent
    path = root_dir / "config/api-surface.yaml"
    assert path.exists(), "config/api-surface.yaml not found"

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    violations = []

    for entry in data:
        if entry.get("status") != "deprecated":
            continue
        endpoint = entry.get("endpoint") or entry.get("path", "unknown")
        method = entry.get("method", "unknown")
        ref = f"{method} {endpoint}"

        if not entry.get("sunset_date") and not entry.get("removal_date") and not entry.get("removal_version"):
            violations.append(f"{ref} missing removal deadline")

        if not entry.get("owner"):
            violations.append(f"{ref} missing owner")

        if not entry.get("replacement") and not entry.get("justification"):
            violations.append(f"{ref} missing replacement or justification")

    assert not violations, (
        f"Deprecated endpoint violations:\n" + "\n".join(f"  - {v}" for v in violations)
    )


def test_feature_flags_deprecated_have_remove_after():
    """
    Ensures all deprecated feature flags have a remove_after field.
    """
    import yaml

    root_dir = Path(__file__).parent.parent.parent
    path = root_dir / "config/feature-flags.yaml"
    assert path.exists(), "config/feature-flags.yaml not found"

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    violations = []

    for entry in data:
        if not isinstance(entry, dict) or entry.get("status") != "deprecated":
            continue
        name = entry.get("name", "UNNAMED")
        if not entry.get("remove_after"):
            violations.append(f"Flag '{name}' missing remove_after")
        if not entry.get("replacement"):
            violations.append(f"Flag '{name}' missing replacement")
        if not entry.get("owner"):
            violations.append(f"Flag '{name}' missing owner")

    assert not violations, (
        "Deprecated feature flag violations:\n" + "\n".join(f"  - {v}" for v in violations)
    )
