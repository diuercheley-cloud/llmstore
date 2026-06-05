import os
import json
import hashlib
import subprocess
import pytest

def test_airgap_bundle_verification():
    # 1. Create a valid bundle
    bundle_path = "/tmp/test_v1.2.0.stack"
    subprocess.run(["python3", "scripts/airgap/create_bundle.py", "--version", "1.2.0", "--out", bundle_path], check=True)
    
    # 2. Verify it
    res = subprocess.run(["python3", "scripts/airgap/verify_bundle.py", "--bundle", bundle_path], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Successfully verified" in res.stdout
    
    # 3. Tamper with the bundle
    with open(bundle_path, "r") as f:
        data = json.load(f)
    data["payload"]["app.bin"] = "TAMPERED_CONTENT"
    with open(bundle_path, "w") as f:
        json.dump(data, f)
        
    # 4. Verification should fail
    res_fail = subprocess.run(["python3", "scripts/airgap/verify_bundle.py", "--bundle", bundle_path], capture_output=True, text=True)
    assert res_fail.returncode != 0
    assert "Hash mismatch" in res_fail.stdout
    
    os.remove(bundle_path)

def test_airgap_dry_run():
    bundle_path = "/tmp/test_dryrun.stack"
    subprocess.run(["python3", "scripts/airgap/create_bundle.py", "--version", "1.2.0", "--out", bundle_path], check=True)
    
    # Run with dry-run
    res = subprocess.run(["python3", "scripts/airgap/apply_bundle.py", "--bundle", bundle_path, "--dry-run"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Dry-run mode" in res.stdout
    assert "Would apply: app.bin" in res.stdout
    
    os.remove(bundle_path)

def test_airgap_downgrade_protection():
    bundle_path = "/tmp/test_downgrade.stack"
    # Current is 1.1.0 in scripts/airgap/apply_bundle.py
    subprocess.run(["python3", "scripts/airgap/create_bundle.py", "--version", "1.0.0", "--out", bundle_path], check=True)
    
    res = subprocess.run(["python3", "scripts/airgap/apply_bundle.py", "--bundle", bundle_path], capture_output=True, text=True)
    assert res.returncode != 0
    assert "Downgrade detected" in res.stdout
    
    # Force downgrade
    res_force = subprocess.run(["python3", "scripts/airgap/apply_bundle.py", "--bundle", bundle_path, "--force-downgrade"], capture_output=True, text=True)
    assert res_force.returncode == 0
    assert "Update to version 1.0.0 applied" in res_force.stdout
    
    os.remove(bundle_path)
