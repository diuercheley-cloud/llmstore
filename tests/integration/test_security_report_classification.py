import json
import shutil
import subprocess
from pathlib import Path


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(["git", "checkout", "-b", "feature/test-security-report"], cwd=path, check=True)


def test_security_report_classification(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_repo(repo_root)

    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir()
    shutil.copy2("scripts/validators/check-secrets.sh", scripts_dir / "check-secrets.sh")
    shutil.copy2(
        "scripts/validators/security-report-local.sh", scripts_dir / "security-report-local.sh"
    )

    (repo_root / "docker-compose.yml").write_text("services:\n  app:\n    image: busybox\n")
    (repo_root / "tests" / "fixtures").mkdir(parents=True)
    (repo_root / "releases" / "v1").mkdir(parents=True)

    (repo_root / "tests" / "fixtures" / "fake_secret_sample.txt").write_text(
        "FAKE SECRET FOR TESTS ONLY\n" + "sk-" + "thisisafakebutlongenoughsecret12345\n"
    )
    (repo_root / "releases" / "v1" / "bundle.txt").write_text(
        "ADMIN_TOKEN=" + "very-secret-token-1234567890" + "\n"
    )

    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(
        [
            "chmod",
            "+x",
            "scripts/validators/check-secrets.sh",
            "scripts/validators/security-report-local.sh",
        ],
        cwd=repo_root,
        check=True,
    )

    output_dir = repo_root / "artifacts" / "security-reports"
    result = subprocess.run(
        ["./scripts/validators/security-report-local.sh", "--output-dir", str(output_dir)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode in {0, 1}

    report_files = list(output_dir.glob("*/security-report.json"))
    assert len(report_files) == 1
    data = json.loads(report_files[0].read_text())

    checks = {check["id"]: check for check in data["checks"]}
    assert checks["sec-secrets-all"]["status"] in {"skip", "warn", "fail"}
    assert checks["sec-secrets-all"]["meta"]["classifications"]["fixture_expected"] >= 1
    assert checks["sec-secrets-artifacts"]["status"] == "warn"

    fixture_check = checks["sec-secrets-all-fixture_expected"]
    assert fixture_check["status"] == "skip"
    assert fixture_check["meta"]["classification"] == "fixture_expected"

    release_check = checks["sec-secrets-artifacts-obsolete_release_file"]
    assert release_check["status"] == "warn"
    assert "releases/v1/bundle.txt" in release_check["evidence"]
