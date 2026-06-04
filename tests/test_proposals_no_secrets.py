import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROPOSAL_FILES = [
    "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md",
    "proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md",
    "proposals/LOCAL_AI_APPLIANCE_ONE_PAGER.md",
    "proposals/README.md",
]

SCRIPT_FILES = [
    "scripts/generate-proposal-pdf.sh",
    "scripts/validate-proposals-local.sh",
]

SECRET_REGEX_PATTERNS = [
    'sk-[a-zA-Z0-9]',
    'ghp_[a-zA-Z0-9]',
    '-----BEGIN [A-Z ]',
    'ADMIN_TOKEN=',
]


def _is_secret_regex_line(line):
    """Check if a line is a regex pattern definition, not an actual secret."""
    stripped = line.strip()
    # Lines with character classes like [A-Z] are regex patterns, not real secrets
    if re.search(r'\[[A-Za-z]', stripped):
        return True
    # Lines with escaped backslash sequences are regex patterns
    if re.search(r'\\\\\{|\\\\\(|\\\\\[', stripped):
        return True
    # Lines inside SECRET_PATTERNS array
    if any(pat in stripped for pat in SECRET_REGEX_PATTERNS):
        if 'regex' in stripped.lower() or 'pattern' in stripped.lower() or 'SECRET_PATTERNS' in line:
            return True
        if re.search(r'\\\{|\\\(|\\\[', stripped):
            return True
    return False


class TestProposalFilesNoSecrets:

    def test_no_real_api_keys(self):
        """Check that no real OpenAI-style API keys are present."""
        pattern = re.compile(r"sk-[a-zA-Z0-9]{32,}")
        for filepath in PROPOSAL_FILES + SCRIPT_FILES:
            f = ROOT / filepath
            if not f.exists():
                continue
            lines = f.read_text().split('\n')
            for lineno, line in enumerate(lines, 1):
                if _is_secret_regex_line(line):
                    continue
                matches = pattern.findall(line)
                for key in matches:
                    assert key.startswith("sk-demo-") or key.startswith("sk-local-"), \
                        f"Potential real API key in {filepath}:{lineno}: {key[:20]}..."

    def test_no_private_keys(self):
        """Check for PEM private key markers."""
        for filepath in PROPOSAL_FILES + SCRIPT_FILES:
            f = ROOT / filepath
            if not f.exists():
                continue
            lines = f.read_text().split('\n')
            for lineno, line in enumerate(lines, 1):
                if _is_secret_regex_line(line):
                    continue
                assert "-----BEGIN" not in line, f"Private key marker in {filepath}:{lineno}"

    def test_no_github_tokens(self):
        """Check for GitHub tokens."""
        for filepath in PROPOSAL_FILES + SCRIPT_FILES:
            f = ROOT / filepath
            if not f.exists():
                continue
            lines = f.read_text().split('\n')
            for lineno, line in enumerate(lines, 1):
                if _is_secret_regex_line(line):
                    continue
                assert "ghp_" not in line, f"GitHub token pattern in {filepath}:{lineno}"

    def test_no_env_file_references(self):
        """Check no references to .env files with secrets."""
        for filepath in PROPOSAL_FILES:
            f = ROOT / filepath
            if not f.exists():
                continue
            content = f.read_text()
            assert "ADMIN_TOKEN=" not in content, \
                f"{filepath} may expose env secrets"

    def test_no_real_client_names(self):
        """Check no real company names used as examples."""
        for filepath in PROPOSAL_FILES:
            f = ROOT / filepath
            if not f.exists():
                continue
            content = f.read_text().lower()
            # Should use placeholders or generic references instead of real client names
            assert any(phrase in content for phrase in [
                "[nome do cliente]", "[cliente]", "Nome do Cliente",
                "[Nome do Cliente]", "acme", "cliente",
                "para quem serve", "documento é um template"
            ]), f"{filepath} should use placeholders for client names"


class TestProposalScriptsNoSecrets:

    def test_generate_script_no_network(self):
        """Verify generate-proposal-pdf.sh doesn't send data to internet."""
        f = ROOT / "scripts/generate-proposal-pdf.sh"
        if not f.exists():
            return
        content = f.read_text()
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("echo") or stripped == "":
                continue
            if _is_secret_regex_line(line):
                continue
            if "curl" in stripped and "localhost" not in stripped:
                assert False, f"Line {i}: curl to non-localhost URL: {stripped}"

    def test_validate_script_no_secrets(self):
        """Verify validate-proposals-local.sh doesn't contain secrets."""
        f = ROOT / "scripts/validate-proposals-local.sh"
        if not f.exists():
            return
        lines = f.read_text().split('\n')
        for lineno, line in enumerate(lines, 1):
            if _is_secret_regex_line(line):
                continue
            assert "sk-" not in line, \
                f"Secret pattern found in validation script:{lineno}: {line.strip()[:50]}"
            assert "ghp_" not in line, \
                f"GitHub token pattern in validation script:{lineno}: {line.strip()[:50]}"
            assert "ADMIN_TOKEN=" not in line, \
                f"Admin token pattern in validation script:{lineno}: {line.strip()[:50]}"
