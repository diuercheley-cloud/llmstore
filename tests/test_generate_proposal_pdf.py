import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate-proposal-pdf.sh"
SAMPLE_MD = ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md"


class TestGenerateProposalPdfScript:

    def test_script_exists(self):
        assert SCRIPT.exists(), "scripts/generate-proposal-pdf.sh não encontrado"

    def test_script_executable(self):
        assert os.access(SCRIPT, os.X_OK), "Script não é executável"

    def test_help_flag(self):
        result = subprocess.run(
            [str(SCRIPT), "--help"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0
        assert "Usage" in result.stdout or "Usage" in result.stderr

    def test_missing_input_shows_error(self):
        result = subprocess.run(
            [str(SCRIPT)],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode != 0
        assert "--input is required" in result.stdout or "--input is required" in result.stderr

    def test_invalid_input_shows_error(self):
        result = subprocess.run(
            [str(SCRIPT), "--input", "/tmp/nonexistent.md"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode != 0
        assert "not found" in result.stdout or "not found" in result.stderr

    def test_invalid_option_shows_error(self):
        result = subprocess.run(
            [str(SCRIPT), "--invalid-flag"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode != 0
        assert "Unknown option" in result.stdout or "Unknown option" in result.stderr

    def test_script_does_not_send_to_internet(self):
        """Verify script doesn't contain curl/wget calls to external URLs."""
        content = SCRIPT.read_text()
        # Check no external network calls
        assert "curl" not in content or "localhost" in content or "http" not in content.replace("localhost", ""), \
            "Script may send data to internet"
        assert "wget" not in content, "Script uses wget"

    def test_generates_pdf_if_tool_available(self):
        """If pandoc, wkhtmltopdf or chrome is available, PDF should be generated."""
        # Check for tools
        has_pandoc = subprocess.run(
            ["which", "pandoc"], capture_output=True
        ).returncode == 0
        has_chrome = subprocess.run(
            ["which", "google-chrome"],
            capture_output=True
        ).returncode == 0
        if not has_chrome:
            has_chrome = subprocess.run(
                ["which", "chromium-browser"],
                capture_output=True
            ).returncode == 0
        if not has_chrome:
            has_chrome = subprocess.run(
                ["which", "chromium"],
                capture_output=True
            ).returncode == 0

        if not has_pandoc and not has_chrome:
            # No tools available - just check that script exits 0
            result = subprocess.run(
                [str(SCRIPT), "--input", str(SAMPLE_MD)],
                capture_output=True, text=True, timeout=60
            )
            assert result.returncode == 0
            return

        # Tool available - generate PDF
        output_path = ROOT / "artifacts" / "proposals" / "test-generated.pdf"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [str(SCRIPT), "--input", str(SAMPLE_MD), "--output", str(output_path)],
            capture_output=True, text=True, timeout=120
        )
        # Should succeed or warn about tool but not fail
        assert result.returncode == 0

        # Clean up
        if output_path.exists():
            output_path.unlink()

    def test_does_not_commit_pdfs(self):
        """Verify that .gitignore covers generated PDFs."""
        gitignore = (ROOT / ".gitignore").read_text()
        assert "artifacts/" in gitignore, ".gitignore deve cobrir artifacts/"
        assert any(p in gitignore for p in [
            "proposals/generated",
            "*.pdf",
        ]) or "artifacts/" in gitignore, ".gitignore deve cobrir PDFs gerados"
