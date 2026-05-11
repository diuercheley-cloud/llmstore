import subprocess
import os
import glob
import json

def test_report_generation():
    output_dir = "artifacts/pytest-checklists"
    result = subprocess.run([
        "./scripts/pre-client-checklist-local.sh", 
        "--demo", 
        "--skip-lmstudio", 
        "--skip-rag", 
        "--skip-tts",
        "--output-dir", output_dir
    ], capture_output=True, text=True)
    
    # Check if a directory was created
    dirs = glob.glob(f"{output_dir}/*/")
    assert len(dirs) > 0, "No output directory was created"
    
    latest_dir = max(dirs, key=os.path.getmtime)
    
    json_file = os.path.join(latest_dir, "checklist.json")
    md_file = os.path.join(latest_dir, "checklist.md")
    
    assert os.path.exists(json_file), f"JSON file missing: {json_file}"
    assert os.path.exists(md_file), f"MD file missing: {md_file}"
    
    # Check JSON content
    with open(json_file, 'r') as f:
        data = json.load(f)
        assert "status" in data
        assert data["status"] in ["GO", "GO_WITH_WARNINGS", "NO_GO"]
        assert data["mode"] == "demo"
