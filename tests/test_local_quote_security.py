import os
import subprocess
import pytest

def test_quotes_in_gitignore():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    gitignore_path = os.path.join(root_dir, ".gitignore")
    
    with open(gitignore_path, 'r') as f:
        content = f.read()
    
    # Either artifacts/ or artifacts/quotes should be ignored
    assert "artifacts/" in content or "artifacts/quotes" in content

def test_no_secrets_in_generated_quotes():
    # Run a few generations
    subprocess.run(["bash", "scripts/generate-local-quote.sh", "--company-name", "SecretTest", "--plan", "Basic"], check=True)
    
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    quotes_dir = os.path.join(root_dir, "artifacts", "quotes")
    
    # Grep for common secret patterns
    # We use a broad grep to be safe
    # Note: we expect some failure if no matches found, which is what we want
    try:
        # If grep finds something, it returns 0. We want it to NOT find anything.
        result = subprocess.run(
            ["grep", "-rE", "API_KEY|SECRET|PASSWORD", quotes_dir],
            capture_output=True, text=True
        )
        assert result.returncode != 0, f"Potential secrets found in quotes: {result.stdout}"
    except FileNotFoundError:
        # grep might not be installed, but it should be on linux
        pass
