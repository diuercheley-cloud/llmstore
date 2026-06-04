import subprocess


def test_release_gate_help_error():
    # Run with empty tag, should fail with tag error
    res = subprocess.run(
        ["bash", "scripts/release-gate.sh"],
        capture_output=True,
        text=True
    )
    assert res.returncode != 0
    assert "Tag de release não fornecida" in res.stdout or "Tag de release não fornecida" in res.stderr

def test_production_release_gate_tag_validation():
    # Run production release gate with non-production tag
    res = subprocess.run(
        ["bash", "scripts/production-agentic-release-gate.sh", "v1.0.0-invalid"],
        capture_output=True,
        text=True
    )
    assert res.returncode != 0
    assert "deve conter uma das seguintes palavras-chave" in res.stdout or "deve conter uma das seguintes palavras-chave" in res.stderr
