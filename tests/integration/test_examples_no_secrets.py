import glob
import os

OUT_OF_SCOPE_EXAMPLE_NAMES = {
    "embeddings.sh",
    "embeddings.py",
    "embeddings.js",
    "responses.sh",
    "responses.py",
    "responses.js",
}


def _is_release_scoped_example(file_path: str) -> bool:
    return os.path.basename(file_path) not in OUT_OF_SCOPE_EXAMPLE_NAMES


def test_no_hardcoded_keys():
    """Verify that no API keys are hardcoded in example files."""
    example_files = []
    for d in ["curl", "python", "node"]:
        example_files.extend(glob.glob(f"examples/{d}/**/*.*", recursive=True))
    
    # Common patterns that might indicate a hardcoded key
    # We want to make sure they are using environment variables
    secret_patterns = [
        "sk-", # OpenAI style
        "api_key = \"",
        "API_KEY = \"",
        "const API_KEY = \"",
    ]
    
    for file_path in example_files:
        if os.path.isdir(file_path) or not _is_release_scoped_example(file_path):
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            for pattern in secret_patterns:
                # Allow the pattern if it's followed by something that looks like an env var fetch
                # or if it's in a comment/README explaining how to use it.
                if pattern in content:
                    # Check if it's an assignment to a string literal with actual content
                    # Simple heuristic: if it's 'API_KEY = "something"' and 'something' is not empty/placeholder
                    if "os.getenv" in content or "process.env" in content or "${CLIENT_API_KEY}" in content:
                        continue
                    
                    # If it's the README, it's okay to have examples of how to export
                    if "README.md" in file_path:
                        continue
                        
                    assert False, f"Potential hardcoded key pattern '{pattern}' found in {file_path}"

def test_env_var_usage():
    """Verify that example files use CLIENT_API_KEY environment variable."""
    example_files = []
    for d in ["curl", "python", "node"]:
        example_files.extend(glob.glob(f"examples/{d}/**/*.*", recursive=True))
    
    for file_path in example_files:
        if os.path.isdir(file_path) or "README.md" in file_path or not _is_release_scoped_example(file_path):
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "CLIENT_API_KEY" in content, f"CLIENT_API_KEY not found in {file_path}"
