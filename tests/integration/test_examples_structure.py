import os


def test_examples_directory_structure():
    """Verify that all expected example files exist."""
    expected_files = [
        "examples/curl/chat.sh",
        "examples/curl/models.sh",
        "examples/curl/streaming.sh",
        "examples/python/chat.py",
        "examples/python/streaming.py",
        "examples/python/rag_query.py",
        "examples/node/chat.js",
        "examples/node/streaming.js",
        "examples/node/rag_query.js",
        "examples/README.md",
        "scripts/legacy/validate-examples-local.sh",
    ]

    for file_path in expected_files:
        assert os.path.exists(file_path), f"Missing expected file: {file_path}"


def test_scripts_are_executable():
    """Verify that shell scripts have execution permissions."""
    scripts = [
        "examples/curl/chat.sh",
        "examples/curl/models.sh",
        "examples/curl/streaming.sh",
        "scripts/legacy/validate-examples-local.sh",
    ]

    for script in scripts:
        assert os.access(script, os.X_OK), f"Script not executable: {script}"
