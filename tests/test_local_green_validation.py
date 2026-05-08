from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_validate_local_green_script_exists():
    script = ROOT / "scripts" / "validate-local-green.sh"
    assert script.exists()


def test_validate_local_green_runs_expected_commands():
    content = (ROOT / "scripts" / "validate-local-green.sh").read_text(encoding="utf-8")
    assert "./scripts/check-secrets.sh --all" in content
    assert "docker compose" in content
    assert "./scripts/validate-local-production-full.sh" in content
    assert "python -m pytest -q" in content
    assert "./scripts/dr-test-local.sh" in content
    assert "artifacts/local-green-validation" in content
