from pathlib import Path


def test_gitignore_contains_security_patterns():
    gitignore_path = Path(".gitignore")
    assert gitignore_path.exists(), ".gitignore file must exist"
    
    content = gitignore_path.read_text()
    
    required_patterns = [
        ".env",
        ".env.*",
        "!.env.example",
        "!.env.local.example",
        ".local/",
        "artifacts/",
        "exports/",
        "backups/",
        "data/rag_uploads/",
        "models/",
        "*.gguf",
        "*.safetensors",
        "*.bin",
        "releases/**/*.tar.gz",
        "releases/**/logs/",
        "releases/**/raw-results*",
        "__pycache__/",
        ".pytest_cache/",
        ".mypy_cache/",
        ".ruff_cache/",
        "node_modules/",
        "*.pem",
        "*.key",
        "!tests/fixtures/fake_*.pem",
        "!tests/fixtures/fake_*.key",
        "!releases/**/release-manifest.json",
        "!releases/**/summary.json",
        "!releases/**/summary.md",
        "!releases/**/bundle-manifest.json",
        "!releases/**/bundle-checksums.sha256"
    ]
    
    for pattern in required_patterns:
        assert pattern in content, f"Missing required pattern: {pattern} in .gitignore"
