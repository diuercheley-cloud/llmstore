import subprocess
import os
import tarfile
import json
import pytest
from pathlib import Path

@pytest.fixture
def clean_releases():
    release_dir = Path("releases/v-test-pytest")
    if release_dir.exists():
        import shutil
        shutil.rmtree(release_dir)
    yield "v-test-pytest"
    if release_dir.exists():
        import shutil
        shutil.rmtree(release_dir)

def test_bundle_creation_basic(clean_releases):
    version = clean_releases
    cmd = ["./scripts/create-release-bundle.sh", "--version", version]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    
    archive_path = Path(f"releases/{version}/llm-inference-stack-{version}.tar.gz")
    manifest_path = Path(f"releases/{version}/bundle-manifest.json")
    checksum_path = Path(f"releases/{version}/bundle-checksums.sha256")
    
    assert archive_path.exists()
    assert manifest_path.exists()
    assert checksum_path.exists()
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
        assert manifest["version"] == version
        assert manifest["secrets_scan_passed"] is True
        assert manifest["models_included"] is False

def test_bundle_inclusions(clean_releases):
    version = clean_releases
    # Try including everything
    cmd = [
        "./scripts/create-release-bundle.sh", 
        "--version", version, 
        "--include-docs", 
        "--include-examples", 
        "--include-demo"
    ]
    subprocess.run(cmd, check=True)
    
    archive_path = Path(f"releases/{version}/llm-inference-stack-{version}.tar.gz")
    
    with tarfile.open(archive_path, "r:gz") as tar:
        names = tar.getnames()
        # All paths in tar start with the bundle name
        root = f"llm-inference-stack-{version}"
        assert f"{root}/docs/README.md" in names or f"{root}/docs/INSTALL.md" in names
        assert f"{root}/examples/README.md" in names
        assert f"{root}/demo/rag-documents" in names

def test_bundle_exclusions(clean_releases):
    version = clean_releases
    subprocess.run(["./scripts/create-release-bundle.sh", "--version", version], check=True)
    
    archive_path = Path(f"releases/{version}/llm-inference-stack-{version}.tar.gz")
    
    with tarfile.open(archive_path, "r:gz") as tar:
        names = tar.getnames()
        root = f"llm-inference-stack-{version}"
        
        # Check forbidden things
        for name in names:
            assert ".git/" not in name
            assert ".venv/" not in name
            assert ".env" not in name or ".env.example" in name or ".env.local.example" in name
            assert "models/" not in name
            assert ".gguf" not in name
            assert "data/rag_uploads/" not in name

def test_validate_bundle_script():
    # This script creates and validates its own bundle
    result = subprocess.run(["./scripts/validate-release-bundle.sh"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Bundle validation PASSED!" in result.stdout
