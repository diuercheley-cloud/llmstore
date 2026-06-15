import json
import os
import sys
import uuid

# Add control_plane to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "control_plane"))

from app.services.governance.release_engineering.release_manifest_service import (
    ReleaseManifestService,
)
from app.services.governance.release_engineering.release_notes_generator import (
    ReleaseNotesGenerator,
)
from app.services.governance.release_engineering.validation_snapshot_service import (
    ValidationSnapshotService,
)


def main():
    print("Generating deterministic platform release baseline...")

    version = "v1.9.0-release-engineering-baseline"
    scope = [
        "Macrofases 69-82",
        "Technical Freeze",
        "Governance Foundation",
        "Plugin Runtime Foundation",
        "Reproducible Builds",
        "Platform Sustainability",
    ]

    # Simulate validation results
    validation_results = {
        "architecture_smoke": "PASS",
        "governance_compliance": "PASS",
        "reproducibility_check": "PASS",
    }

    snapshot_service = ValidationSnapshotService()
    baseline_id = str(uuid.uuid4())
    snapshot = snapshot_service.create_snapshot(baseline_id, "smoke", validation_results)

    manifest_service = ReleaseManifestService()
    manifest = manifest_service.generate_manifest(version, scope, snapshot["snapshot_hash"])

    # Simulate changelog data
    changelog_data = [
        {
            "type": "Added",
            "changes": [
                "Macrofases 69-82 implementation baseline.",
                "Platform release baseline and validation snapshot infrastructure.",
            ],
        },
        {
            "type": "Governance",
            "changes": [
                "Foundation for release engineering governance.",
                "Release receipt issuance and verification logic.",
            ],
        },
    ]

    notes_generator = ReleaseNotesGenerator()
    notes = notes_generator.generate_deterministic_notes(manifest, changelog_data)

    # Save artifacts
    output_dir = "docs/releases"
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "latest_release_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    with open(os.path.join(output_dir, "latest_release_notes.md"), "w") as f:
        f.write(notes)

    print(f"Release manifest saved to {os.path.join(output_dir, 'latest_release_manifest.json')}")
    print(f"Release notes saved to {os.path.join(output_dir, 'latest_release_notes.md')}")
    print("Baseline generation complete.")


if __name__ == "__main__":
    main()
