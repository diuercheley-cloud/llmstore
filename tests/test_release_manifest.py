import os
import json
import subprocess
import pytest
import shutil

def test_release_manifest_script_exists():
    assert os.path.exists("scripts/generate-release-manifest.sh")
    assert os.path.exists("scripts/release-local-production.sh")

def test_manifest_content():
    version = "v9.9.9-test-manifest"
    artifact_dir = "/tmp/fake-artifact-dir"
    release_dir = f"releases/{version}"
    manifest_path = f"{release_dir}/release-manifest.json"
    
    # Ensure clean state
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
        
    try:
        # Run script
        result = subprocess.run([
            "bash", "scripts/generate-release-manifest.sh",
            "--version", version,
            "--artifact-dir", artifact_dir,
            "--validation-result", "success"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert os.path.exists(manifest_path)
        
        with open(manifest_path, "r") as f:
            data = json.load(f)
            
        # Validate mandatory fields
        required_fields = [
            "release_name", "version", "git_branch", "git_commit",
            "git_tags_pointing_to_commit", "generated_at",
            "validation_artifact_path", "summary_json_path", "summary_md_path",
            "models_included", "rag_uploads_included", "psp_integration",
            "pix_real_billing", "localhost_mode", "known_limitations",
            "validation_result"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
            
        assert data["version"] == version
        assert data["validation_artifact_path"] == artifact_dir
        assert data["models_included"] is False
        assert data["rag_uploads_included"] is False
        assert data["psp_integration"] is False
        assert data["pix_real_billing"] is False
        assert data["localhost_mode"] is True
        
        # Security check: no obvious secrets
        manifest_str = json.dumps(data)
        # Avoid checking 'key' in a way that flags 'docker_compose_files' or similar
        forbidden_patterns = ["password=", "secret=", "key="]
        for pattern in forbidden_patterns:
            assert pattern not in manifest_str.lower(), f"Potential secret pattern found: {pattern}"

    finally:
        if os.path.exists(release_dir):
            shutil.rmtree(release_dir)

if __name__ == "__main__":
    # If run directly
    pytest.main([__file__])
