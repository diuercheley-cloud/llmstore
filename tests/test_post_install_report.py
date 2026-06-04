import glob
import json
import os


def test_report_generation():
    # Find latest test report
    base_dir = "artifacts/test-pytest-output"
    if not os.path.exists(base_dir):
        return # Skip if not run yet
    
    dirs = glob.glob(f"{base_dir}/*")
    if not dirs:
        return
        
    latest_dir = max(dirs, key=os.path.getmtime)
    json_path = os.path.join(latest_dir, "post-install-report.json")
    md_path = os.path.join(latest_dir, "post-install-report.md")
    
    assert os.path.exists(json_path)
    assert os.path.exists(md_path)
    
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    assert "score" in data
    assert data["score"] in ["INSTALLED_READY", "INSTALLED_WITH_WARNINGS", "INSTALLATION_FAILED"]
    assert "flags" in data
