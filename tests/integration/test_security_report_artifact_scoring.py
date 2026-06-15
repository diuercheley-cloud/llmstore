import json

# tests/test_security_report_artifact_scoring.py
# FAKE SECRET FOR TESTS ONLY
import shutil
import subprocess
from pathlib import Path


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(["git", "checkout", "-b", "feature/test-artifact-scoring"], cwd=path, check=True)


def test_security_report_artifact_scoring(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_repo(repo_root)

    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir()
    shutil.copy2("scripts/validators/check-secrets.sh", scripts_dir / "check-secrets.sh")
    shutil.copy2(
        "scripts/validators/security-report-local.sh", scripts_dir / "security-report-local.sh"
    )
    shutil.copy2(
        "scripts/backup/redact-local-sensitive-artifacts.sh",
        scripts_dir / "redact-local-sensitive-artifacts.sh",
    )

    # Ensure redact script exists or mock it
    if not (scripts_dir / "redact-local-sensitive-artifacts.sh").exists():
        (scripts_dir / "redact-local-sensitive-artifacts.sh").write_text(
            "#!/bin/bash\necho 'mock redact'"
        )
        (scripts_dir / "redact-local-sensitive-artifacts.sh").chmod(0o755)

    (repo_root / "docker-compose.yml").write_text("services:\n  app:\n    image: busybox\n")
    (repo_root / "tests" / "fixtures").mkdir(parents=True)
    (repo_root / "releases").mkdir(parents=True)
    (repo_root / "artifacts").mkdir(parents=True)
    (repo_root / ".gitignore").write_text("artifacts/\n")

    # 1. Real secret in tracked file (FAIL)
    (repo_root / "config.py").write_text("ADMIN_TOKEN=sk-real-secret-12345678901234567890\n")

    # 2. Redacted token in ignored artifact (PASS/INFO)
    (repo_root / "artifacts" / "scan_log.txt").write_text("Found sk-***masked*** in some file\n")

    # 3. Authorized fixture (PASS/INFO)
    (repo_root / "tests" / "fixtures" / "fake_key.pem").write_text(
        "FAKE TEST KEY - DO NOT USE\n-----BEGIN PRIVATE KEY-----\n...\n"
    )

    # 4. Secret in ignored artifact (WARN/PASS_WITH_WARNINGS)
    (repo_root / "artifacts" / "old_artifact.txt").write_text(
        "ADMIN_TOKEN=sk-should-be-warn-but-ignored-123\n"
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

    output_dir = repo_root / "report_out"
    # Run first time with real secret in tracked file -> should FAIL
    result = subprocess.run(
        ["./scripts/validators/security-report-local.sh", "--output-dir", str(output_dir)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert "Security Report Generated: FAIL" in result.stdout

    report_files = list(output_dir.glob("*/security-report.json"))
    data = json.loads(report_files[0].read_text())
    assert data["score"] == "FAIL"

    # Now remove the real secret from tracked file
    (repo_root / "config.py").write_text("ADMIN_TOKEN=os.environ.get('ADMIN_TOKEN')\n")
    subprocess.run(["git", "add", "config.py"], cwd=repo_root, check=True)

    # Run again -> should be PASS_WITH_WARNINGS because of old_artifact.txt (ignored but not redacted)
    shutil.rmtree(output_dir)
    result = subprocess.run(
        ["./scripts/validators/security-report-local.sh", "--output-dir", str(output_dir)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if "Security Report Generated: PASS_WITH_WARNINGS" not in result.stdout:
        print("\n--- DEBUG: STDOUT ---")
        print(result.stdout)
        print("--- DEBUG: JSON REPORT ---")
        report_json = list(output_dir.glob("*/security-report.json"))[0]
        print(report_json.read_text())

    assert "Security Report Generated: PASS_WITH_WARNINGS" in result.stdout
    data = json.loads(list(output_dir.glob("*/security-report.json"))[0].read_text())
    assert data["score"] == "PASS_WITH_WARNINGS"

    # Now redact old_artifact.txt
    (repo_root / "artifacts" / "old_artifact.txt").write_text("ADMIN_TOKEN=***masked***\n")

    # Run again -> should be PASS
    shutil.rmtree(output_dir)
    result = subprocess.run(
        ["./scripts/validators/security-report-local.sh", "--output-dir", str(output_dir)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert "Security Report Generated: PASS" in result.stdout
    data = json.loads(list(output_dir.glob("*/security-report.json"))[0].read_text())
    assert data["score"] == "PASS"

    # Verify MD report structure
    md_file = list(output_dir.glob("*/security-report.md"))[0]
    md_content = md_file.read_text()
    assert "## Blocking Findings (Action Required)" in md_content
    assert "## Warnings" in md_content
    assert "## Informational & Redacted Artifacts" in md_content
    assert "## All Passed Checks" in md_content
