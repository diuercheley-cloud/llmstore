import os
import re


def validate_naming_consistency():
    print("Validating naming and API consistency...")

    # Preferred terms
    standard_terms = [
        "immutable_hash",
        "payload_hash",
        "replay_safe",
        "replay_verifiable",
        "offline_verifiable",
        "signature_placeholder",
        "advisory_only",
        "dry_run",
        "client_id",
    ]

    # Patterns that might indicate legacy naming
    legacy_patterns = [
        (r"raw_hash", "Consider using payload_hash or immutable_hash"),
        (r"tenant_uuid", "Use client_id for consistency"),
        (r"simulation_mode", "Use dry_run for consistency"),
        (r"blocking_mode", "Use advisory_only (inverse) for consistency"),
    ]

    root_dir = os.path.join(os.path.dirname(__file__), "..", "control_plane")
    found_legacy = 0

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                    for pattern, msg in legacy_patterns:
                        if re.search(pattern, content):
                            print(f"CONSISTENCY WARNING: {msg} in {path}")
                            found_legacy += 1

    print(f"\nNaming consistency check complete. Found {found_legacy} potential legacy terms.")
    return True


if __name__ == "__main__":
    validate_naming_consistency()
