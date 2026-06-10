import json
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
GENERATOR = ROOT_DIR / "scripts" / "generate-release-history.sh"
VALIDATOR = ROOT_DIR / "scripts" / "validate-release-history.sh"
OUTPUT_MD = ROOT_DIR / "docs" / "RELEASE_HISTORY.md"
ARTIFACTS_DIR = ROOT_DIR / "artifacts" / "release-history"


def _latest_report_dir():
    if not ARTIFACTS_DIR.exists():
        return None
    dirs = sorted(ARTIFACTS_DIR.iterdir())
    return str(dirs[-1]) if dirs else None


def test_generator_script_exists():
    assert GENERATOR.exists()
    assert GENERATOR.stat().st_mode & 0o111


def test_validator_script_exists():
    assert VALIDATOR.exists()
    assert VALIDATOR.stat().st_mode & 0o111


def test_generate_exits_clean():
    result = subprocess.run(
        [str(GENERATOR)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_generate_produces_output():
    result = subprocess.run(
        [str(GENERATOR)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert OUTPUT_MD.exists(), "RELEASE_HISTORY.md not generated"
    content = OUTPUT_MD.read_text()
    assert "Release History" in content
    # Should list at least 10 releases
    assert content.count("| `v") >= 10


def test_generate_produces_json():
    result = subprocess.run(
        [str(GENERATOR)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    report_dir = _latest_report_dir()
    assert report_dir is not None
    report_json = Path(report_dir) / "release-history.json"
    assert report_json.exists()
    data = json.loads(report_json.read_text())
    assert "releases" in data
    assert isinstance(data["releases"], list)


def test_json_contains_required_tags():
    result = subprocess.run(
        [str(GENERATOR)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    report_dir = _latest_report_dir()
    report_json = Path(report_dir) / "release-history.json"
    data = json.loads(report_json.read_text())
    tags = [r["tag"] for r in data["releases"]]
    required = [
        "v1.5.3-local-ops", "v1.5.4-security-cleanup",
        "v1.5.5-security-artifacts-clean", "v1.5.6-runtime-hardening",
        "v1.6.0-openai-compat", "v1.6.1-product-hardening",
        "v1.6.2-installer-polish", "v1.6.3-readiness-cleanup",
        "v1.6.4-customer-demo-pack", "v1.6.5-sales-ops"
    ]
    missing = [t for t in required if t not in tags]
    assert not missing, f"Required tags missing from JSON: {missing}"


def test_each_release_has_required_fields():
    result = subprocess.run(
        [str(GENERATOR)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    report_dir = _latest_report_dir()
    report_json = Path(report_dir) / "release-history.json"
    data = json.loads(report_json.read_text())
    for release in data["releases"]:
        for key in ("tag", "version", "commit", "date", "category", "status"):
            assert key in release, f"Missing {key} in {release.get('tag', '?')}"


def test_validate_passes():
    subprocess.run(
        [str(GENERATOR)],
        capture_output=True, text=True
    )
    result = subprocess.run(
        [str(VALIDATOR)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Validation failed:\n{result.stdout}\n{result.stderr}"
