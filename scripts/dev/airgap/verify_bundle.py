import argparse
import hashlib
import json
import sys

def verify_bundle(bundle_path):
    print(f"Verifying bundle: {bundle_path}")
    
    try:
        with open(bundle_path, "r") as f:
            bundle = json.load(f)
    except Exception as e:
        print(f"Error: Invalid bundle format. {e}")
        return False

    manifest = bundle.get("manifest")
    payload = bundle.get("payload")
    
    if not manifest or not payload:
        print("Error: Missing manifest or payload.")
        return False

    # 1. Verify file hashes
    for file_info in manifest.get("files", []):
        name = file_info["name"]
        expected_hash = file_info["hash"]
        
        if name not in payload:
            print(f"Error: File {name} missing from payload.")
            return False
            
        actual_hash = hashlib.sha256(payload[name].encode()).hexdigest()
        if actual_hash != expected_hash:
            print(f"Error: Hash mismatch for {name}!")
            return False
            
    # 2. Verify Signature (Mock)
    if manifest.get("signature") != "MOCKED_SIGNATURE_OF_MANIFEST":
        print("Error: Invalid bundle signature.")
        return False

    print(f"Successfully verified bundle version {manifest['version']}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()
    if not verify_bundle(args.bundle):
        sys.exit(1)
