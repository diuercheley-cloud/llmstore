import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/dev/generate-client-proposal.sh"

class TestClientProposalSecurity:
    def test_no_secrets_leaked(self):
        output_dir = ROOT / "artifacts/test-py-security"
        cmd = [
            str(SCRIPT),
            "--company-name", "Security Corp",
            "--output-dir", str(output_dir)
        ]
        # We might need to set a dummy ADMIN_TOKEN to check if it leaks
        env = os.environ.copy()
        env["ADMIN_TOKEN"] = "ultra-secret-token-123"
        
        subprocess.run(cmd, check=True, env=env)
        
        # Check all files in the output dir
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = Path(root) / file
                content = file_path.read_text()
                assert "ultra-secret-token-123" not in content, f"Secret leaked in {file}"
                assert "super-secret-admin-token" not in content, f"Default secret leaked in {file}"

    def test_gitignore_compliance(self):
        output_dir = "artifacts/test-py-gitignore"
        # The script creates this dir. We check if it's ignored.
        # Since artifacts/ is ignored, everything under it should be too.
        gitignore = (ROOT / ".gitignore").read_text()
        assert "artifacts/" in gitignore or "artifacts" in gitignore
