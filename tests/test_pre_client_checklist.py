import subprocess


def test_script_help():
    result = subprocess.run(["./scripts/pre-client-checklist-local.sh", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage:" in result.stdout

def test_script_requires_mode():
    result = subprocess.run(["./scripts/pre-client-checklist-local.sh"], capture_output=True, text=True)
    assert result.returncode == 1
    assert "Error: Must specify either --demo or --client-install" in result.stdout

def test_script_demo_mode_executes():
    # We test that it at least attempts to run and doesn't fail on missing mode
    # It might fail due to environmental reasons (no version, etc.), so we just check it starts
    result = subprocess.run(["./scripts/pre-client-checklist-local.sh", "--demo", "--skip-lmstudio", "--skip-rag", "--skip-tts"], capture_output=True, text=True)
    # Could be 0 or 1 depending on system state, but it should print the starting message
    assert "Starting Pre-Client Checklist in demo mode..." in result.stdout
