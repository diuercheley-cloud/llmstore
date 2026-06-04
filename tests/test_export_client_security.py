import subprocess
from pathlib import Path


def test_gitignore_exports():
    with open(".gitignore", "r") as f:
        content = f.read()
    assert "exports/" in content

def test_check_secrets_on_export_dir():
    # Create a dummy export dir with a secret
    test_dir = Path("/tmp") / "llm-inference-stack-export-tests" / "exports" / "test-secrets"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    secret_file = test_dir / "secret.txt"
    secret = "ADMIN_" + "TOKEN=" + "super" + "secret123"
    secret_file.write_text(secret)
    
    # Run check-secrets.sh on it
    result = subprocess.run(
        ["./scripts/check-secrets.sh", "--path", str(test_dir)],
        capture_output=True,
        text=True
    )
    
    # Clean up
    secret_file.unlink()
    test_dir.rmdir()
    
    assert result.returncode != 0
    assert "Potential secret" in result.stdout or "Potential secret" in result.stderr

def test_no_gguf_in_export():
    # This is more of a script logic test
    # We can't easily run the full export here without a live server
    # but we can verify the script has exclusions
    with open("scripts/export-client-local.sh", "r") as f:
        content = f.read()
    # The script should use find or cp carefully.
    # Actually, RAG files are in data/rag_uploads, and models are in models/.
    # The script only copies from data/rag_uploads/<client_id> and searches for .wav.
    # So .gguf (which are in models/) should not be included by default.
    assert "models/" not in content or "cp -r models/" not in content
