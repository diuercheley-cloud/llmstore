import argparse
import json
import sys

from scripts.airgap.verify_bundle import verify_bundle

CURRENT_VERSION = "1.1.0"


def apply_bundle(bundle_path, dry_run=False, force_downgrade=False):
    if not verify_bundle(bundle_path):
        print("Bundle verification failed. Aborting.")
        sys.exit(1)

    with open(bundle_path) as f:
        bundle = json.load(f)

    new_version = bundle["manifest"]["version"]
    print(f"Current Version: {CURRENT_VERSION}")
    print(f"Update Version:  {new_version}")

    # Downgrade protection
    if new_version < CURRENT_VERSION and not force_downgrade:
        print("Error: Downgrade detected. Use --force-downgrade to proceed.")
        sys.exit(1)

    if dry_run:
        print("Dry-run mode: No changes will be applied.")
        for filename in bundle["payload"]:
            print(f"Would apply: {filename}")
        return

    print("Applying update...")
    # Simulate writing files
    for filename, content in bundle["payload"].items():
        print(f"Updating {filename}...")
        # os.write(...)

    print(f"Update to version {new_version} applied successfully.")
    # Audit log
    with open("/tmp/llm-stack-update-audit.log", "a") as log:
        log.write(f"Applied version {new_version} from {bundle_path}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-downgrade", action="store_true")
    args = parser.parse_args()
    apply_bundle(args.bundle, args.dry_run, args.force_downgrade)
