import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "FRESH_MACHINE_VALIDATION.md"
SCRIPT = ROOT / "scripts" / "fresh-machine-readiness-check.sh"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate-fresh-machine-docs.sh"
CHECK_SECRETS = ROOT / "scripts" / "check-secrets.sh"


SECRET_PATTERNS = [
    ("sk-", "OpenAI API key"),
    ("ghp_", "GitHub token"),
    ("ADMIN_TOKEN=", "Admin token"),
    ("JWT_SECRET=", "JWT secret"),
    ("-----BEGIN ", "Private key"),
]

SAFE_EXCEPTIONS = [
    "__redacted__",
    "sk-***masked",
    "sk-demo",
    "sk-local-example",
    "changeme",
    "sk-[a-zA-Z0-9]",
]


def test_document_no_secrets():
    content = DOC.read_text(encoding="utf-8")
    for pat, name in SECRET_PATTERNS:
        if pat in content:
            for safe in SAFE_EXCEPTIONS:
                if safe in content:
                    break
            else:
                assert False, f"Secret '{pat}' ({name}) found in document"


def test_script_no_secrets():
    content = SCRIPT.read_text(encoding="utf-8")
    for pat, name in SECRET_PATTERNS:
        if pat in content:
            for safe in SAFE_EXCEPTIONS:
                if safe in content:
                    break
            else:
                assert False, f"Secret '{pat}' ({name}) found in script"


def test_validate_script_no_secrets():
    content = VALIDATE_SCRIPT.read_text(encoding="utf-8")
    for pat, name in SECRET_PATTERNS:
        if pat in content:
            for safe in SAFE_EXCEPTIONS:
                if safe in content:
                    break
            else:
                assert False, f"Secret '{pat}' ({name}) found in validate script"


def test_check_secrets_on_fresh_machine_doc():
    """Run check-secrets.sh --path on the fresh machine doc and scripts."""
    result = subprocess.run(
        ["bash", str(CHECK_SECRETS), "--path", str(DOC), "--verbose"],
        capture_output=True, text=True, timeout=30,
    )
    print(f"STDOUT:\n{result.stdout}")
    assert result.returncode == 0, f"Secrets found in FRESH_MACHINE_VALIDATION.md:\n{result.stdout}"


def test_check_secrets_on_readiness_script():
    result = subprocess.run(
        ["bash", str(CHECK_SECRETS), "--path", str(SCRIPT), "--verbose"],
        capture_output=True, text=True, timeout=30,
    )
    print(f"STDOUT:\n{result.stdout}")
    assert result.returncode == 0, f"Secrets found in fresh-machine-readiness-check.sh:\n{result.stdout}"


def test_check_secrets_on_validate_script():
    result = subprocess.run(
        ["bash", str(CHECK_SECRETS), "--path", str(VALIDATE_SCRIPT), "--verbose"],
        capture_output=True, text=True, timeout=30,
    )
    print(f"STDOUT:\n{result.stdout}")
    assert result.returncode == 0, f"Secrets found in validate-fresh-machine-docs.sh:\n{result.stdout}"


def test_check_secrets_on_tests():
    test_dir = ROOT / "tests"
    for fname in ["test_fresh_machine_validation_docs.py", "test_fresh_machine_readiness_check.py", "test_fresh_machine_security.py"]:
        fp = test_dir / fname
        if not fp.exists():
            continue
        result = subprocess.run(
            ["bash", str(CHECK_SECRETS), "--path", str(fp), "--verbose"],
            capture_output=True, text=True, timeout=30,
        )
        print(f"STDOUT ({fname}):\n{result.stdout}")
        assert result.returncode == 0, f"Secrets found in {fname}"


def test_no_gguf_download_commands():
    """Document must not reference downloading .gguf files automatically."""
    content = DOC.read_text(encoding="utf-8")
    lines_with_wget = [l for l in content.splitlines() if "wget" in l.lower()]
    lines_with_curl_gguf = [l for l in content.splitlines() if "curl" in l.lower() and "gguf" in l.lower()]
    assert not lines_with_wget, f"Lines with wget found: {lines_with_wget}"
    assert not lines_with_curl_gguf, f"Lines with curl+gguf found: {lines_with_curl_gguf}"


def test_gitignore_protects_env_local():
    gitignore = ROOT / ".gitignore"
    content = gitignore.read_text(encoding="utf-8")
    assert ".env.*" in content or ".env.local" in content, (
        ".gitignore does not protect .env.local"
    )


def test_gitignore_protects_models():
    gitignore = ROOT / ".gitignore"
    content = gitignore.read_text(encoding="utf-8")
    assert "models/" in content, ".gitignore does not protect models/"


def test_gitignore_protects_artifacts():
    gitignore = ROOT / ".gitignore"
    content = gitignore.read_text(encoding="utf-8")
    assert "artifacts/" in content, ".gitignore does not protect artifacts/"


def test_document_no_real_urls():
    content = DOC.read_text(encoding="utf-8")
    for pat in [r"https?://[^\s\)]+\.com[^\s\)]*", r"https?://[^\s\)]+\.io[^\s\)]*"]:
        matches = re.findall(pat, content)
        for url in matches:
            if any(safe in url for safe in ["example", "localhost", "github.com/anomalyco", ".github.io"]):
                continue
            if "nvidia.com" in url or "ubuntu.com" in url:
                continue
            assert False, f"Potentially real URL found: {url}"


def test_document_has_disclaimer():
    content = DOC.read_text(encoding="utf-8")
    lower = content.lower()
    disclaimers = ["não baixa modelos", "nunca baixa modelos", "offline-first", "não expõe secrets", "offline first"]
    assert any(d in lower for d in disclaimers), (
        "Document missing offline/security disclaimer"
    )
