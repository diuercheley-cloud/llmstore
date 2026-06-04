import glob
import os


def test_security_no_secrets():
    base_dir = "artifacts/test-pytest-output"
    if not os.path.exists(base_dir):
        return
    
    dirs = glob.glob(f"{base_dir}/*")
    if not dirs:
        return
        
    latest_dir = max(dirs, key=os.path.getmtime)
    json_path = os.path.join(latest_dir, "post-install-report.json")
    
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            content = f.read().lower()
            assert "password=" not in content
            assert "secret_key" not in content
            assert "token=" not in content
