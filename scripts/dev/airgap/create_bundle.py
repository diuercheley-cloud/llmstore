import argparse
import hashlib
import json
import time


def generate_bundle(version, out_path):
    print(f"Generating Air-gap bundle for version {version}...")

    # Mock files to include
    files = {"app.bin": "MOCKED_BINARY_CONTENT", "config.yaml": "MOCKED_CONFIG_CONTENT"}

    manifest = {
        "version": version,
        "timestamp": int(time.time()),
        "compatibility": {"min_version": "1.0.0", "required_arch": "x86_64"},
        "files": [],
    }

    bundle_data = {}

    for filename, content in files.items():
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        manifest["files"].append({"name": filename, "hash": file_hash})
        bundle_data[filename] = content

    # Signature placeholder
    manifest["signature"] = "MOCKED_SIGNATURE_OF_MANIFEST"

    final_bundle = {"manifest": manifest, "payload": bundle_data}

    with open(out_path, "w") as f:
        json.dump(final_bundle, f, indent=2)

    print(f"Bundle created successfully at {out_path}")
    print(f"Manifest Hash: {hashlib.sha256(json.dumps(manifest).encode()).hexdigest()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    generate_bundle(args.version, args.out)
