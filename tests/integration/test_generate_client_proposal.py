import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/dev/generate-client-proposal.sh"


class TestGenerateClientProposal:
    def test_script_exists(self):
        assert SCRIPT.exists()
        assert os.access(SCRIPT, os.X_OK)

    def test_help_flag(self):
        result = subprocess.run([str(SCRIPT), "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "Usage" in result.stdout

    def test_generate_basic(self):
        output_dir = ROOT / "artifacts/test-py-basic"
        if output_dir.exists():
            import shutil

            shutil.rmtree(output_dir)

        cmd = [
            str(SCRIPT),
            "--company-name",
            "PyTest Corp",
            "--contact-name",
            "Tester",
            "--output-dir",
            str(output_dir),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0
        assert "Proposal generated successfully" in result.stdout

        # Check files
        dirs = list(output_dir.iterdir())
        assert len(dirs) == 1
        timestamp_dir = dirs[0]

        md_files = list(timestamp_dir.glob("*.md"))
        assert len(md_files) == 1
        assert "pytest-corp-proposal.md" in md_files[0].name

        json_files = list(timestamp_dir.glob("*.json"))
        assert len(json_files) == 1
        assert json_files[0].name == "proposal-metadata.json"

        with open(json_files[0]) as f:
            metadata = json.load(f)
            assert metadata["company_name"] == "PyTest Corp"

    def test_dry_run(self):
        output_dir = ROOT / "artifacts/test-py-dry"
        cmd = [
            str(SCRIPT),
            "--company-name",
            "Dry Run Co",
            "--output-dir",
            str(output_dir),
            "--dry-run",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0
        assert "Dry run" in result.stdout
        assert not output_dir.exists()
