# FAKE SECRET FOR TESTS ONLY
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


def get_check_allowlist_func():
    with open("scripts/validators/security-report-local.sh") as f:
        content = f.read()

    lines = content.splitlines()
    func_lines = []
    in_func = False
    for line in lines:
        if line.strip().startswith("def check_allowlist("):
            in_func = True
            func_lines.append(line)
            continue
        if in_func:
            if not line.strip():
                func_lines.append(line)
                continue
            if line.strip() == "EOF":
                break
            lstrip = line.lstrip()
            if len(line) == len(lstrip):
                break
            func_lines.append(line)

    func_code = "\n".join(func_lines)
    local_vars = {}
    global_vars = {"datetime": datetime, "sys": sys, "Path": Path, "allowlist": []}
    exec(func_code, global_vars, local_vars)
    return local_vars["check_allowlist"], global_vars


def test_check_allowlist_valid():
    check_allowlist, globals_dict = get_check_allowlist_func()

    globals_dict["allowlist"] = [
        {
            "file_path": "artifacts/backups/test-backup-run/config/config.env",
            "justification": "Synthetic fake backup for testing",
            "owner": "security-team",
            "expiration_review_date": "2030-01-01",
        }
    ]

    is_allowlisted, reason = check_allowlist(
        "artifacts/backups/test-backup-run/config/config.env", is_versioned=False
    )
    assert is_allowlisted is True
    assert "Allowlisted by security-team" in reason
    assert "Synthetic fake backup for testing" in reason


def test_check_allowlist_expired():
    check_allowlist, globals_dict = get_check_allowlist_func()

    globals_dict["allowlist"] = [
        {
            "file_path": "artifacts/backups/test-backup-run/config/config.env",
            "justification": "Synthetic fake backup for testing",
            "owner": "security-team",
            "expiration_review_date": "2020-01-01",
        }
    ]

    is_allowlisted, reason = check_allowlist(
        "artifacts/backups/test-backup-run/config/config.env", is_versioned=False
    )
    assert is_allowlisted is False


def test_check_allowlist_missing_fields():
    check_allowlist, globals_dict = get_check_allowlist_func()

    globals_dict["allowlist"] = [
        {
            "file_path": "artifacts/backups/test-backup-run/config/config.env",
            "justification": "Synthetic fake backup for testing",
            "expiration_review_date": "2030-01-01",
        }
    ]

    is_allowlisted, reason = check_allowlist(
        "artifacts/backups/test-backup-run/config/config.env", is_versioned=False
    )
    assert is_allowlisted is False


def test_check_allowlist_versioned_file_violation():
    check_allowlist, globals_dict = get_check_allowlist_func()

    globals_dict["allowlist"] = [
        {
            "file_path": "control_plane/app/main.py",
            "justification": "Attempting to allowlist source file",
            "owner": "dev",
            "expiration_review_date": "2030-01-01",
        }
    ]

    is_allowlisted, reason = check_allowlist("control_plane/app/main.py", is_versioned=True)
    assert is_allowlisted is False


def test_script_permission_warning(tmp_path):
    test_script_path = "scripts/test-temp-non-executable.sh"
    with open(test_script_path, "w") as f:
        f.write("#!/bin/bash\necho 'hello'")

    os.chmod(test_script_path, 0o644)

    try:
        out_dir = tmp_path / "sec_reports"
        res = subprocess.run(
            ["./scripts/validators/security-report-local.sh", "--output-dir", str(out_dir)],
            capture_output=True,
            text=True,
        )

        report_jsons = list(out_dir.glob("**/security-report.json"))
        assert len(report_jsons) > 0, "Security report was not generated"

        with open(report_jsons[0]) as fh:
            report_data = json.load(fh)

        perm_check = next((c for c in report_data["checks"] if c["id"] == "perm-scripts"), None)
        assert perm_check is not None
        assert perm_check["status"] == "warn"
        assert "test-temp-non-executable.sh" in perm_check["evidence"]

    finally:
        if os.path.exists(test_script_path):
            os.remove(test_script_path)


def test_secrets_allowlist_integration(tmp_path):
    os.makedirs("artifacts/test-secrets-temp", exist_ok=True)
    temp_env_file = "artifacts/test-secrets-temp/config.env"
    with open(temp_env_file, "w") as f:
        f.write("ADMIN_TOKEN=917b7930cac1eeabff1496a0604249e9216cd8e15281b97657e155593b219f69\n")

    config_dir = Path("config")
    allowlist_file = config_dir / "security-warning-allowlist.yaml"
    backup_file = config_dir / "security-warning-allowlist.yaml.bak"
    if allowlist_file.exists():
        shutil.copy(allowlist_file, backup_file)

    try:
        if allowlist_file.exists():
            os.remove(allowlist_file)

        out_dir_1 = tmp_path / "sec_reports_1"
        res_1 = subprocess.run(
            ["./scripts/validators/security-report-local.sh", "--output-dir", str(out_dir_1)],
            capture_output=True,
            text=True,
        )

        report_jsons_1 = list(out_dir_1.glob("**/security-report.json"))
        assert len(report_jsons_1) > 0
        with open(report_jsons_1[0]) as fh:
            report_data_1 = json.load(fh)

        sec_checks_1 = [
            c for c in report_data_1["checks"] if "test-secrets-temp" in c.get("details", "")
        ]
        assert len(sec_checks_1) > 0
        assert any(c["status"] == "warn" for c in sec_checks_1)

        custom_allowlist = [
            {
                "file_path": temp_env_file,
                "justification": "Synthetic fake token for test cases",
                "owner": "test-suite",
                "expiration_review_date": "2030-01-01",
            }
        ]
        with open(allowlist_file, "w") as f:
            yaml.dump({"allowlist": custom_allowlist}, f)

        out_dir_2 = tmp_path / "sec_reports_2"
        res_2 = subprocess.run(
            ["./scripts/validators/security-report-local.sh", "--output-dir", str(out_dir_2)],
            capture_output=True,
            text=True,
        )

        report_jsons_2 = list(out_dir_2.glob("**/security-report.json"))
        assert len(report_jsons_2) > 0
        with open(report_jsons_2[0]) as fh:
            report_data_2 = json.load(fh)

        sec_checks_2 = [
            c for c in report_data_2["checks"] if "test-secrets-temp" in c.get("details", "")
        ]
        assert len(sec_checks_2) > 0
        assert all(c["status"] in ("skip", "pass") for c in sec_checks_2)

    finally:
        if os.path.exists(temp_env_file):
            os.remove(temp_env_file)
        if os.path.exists("artifacts/test-secrets-temp"):
            shutil.rmtree("artifacts/test-secrets-temp")

        if backup_file.exists():
            shutil.move(backup_file, allowlist_file)
        elif allowlist_file.exists():
            os.remove(allowlist_file)
