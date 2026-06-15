import re
import subprocess
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_LIB = ROOT_DIR / "scripts" / "lib"
ROOT_LIB = ROOT_DIR / "lib"


def test_no_root_lib():
    assert not ROOT_LIB.exists() or not any(ROOT_LIB.iterdir())


def test_scripts_lib_exists():
    assert SCRIPTS_LIB.is_dir()


def test_expected_libs_exist():
    expected = ["operator-errors.sh", "redaction.sh", "validation-logging.sh", "project-root.sh"]
    for lib in expected:
        assert (SCRIPTS_LIB / lib).is_file(), f"Missing {lib} in scripts/dev/lib/"


def test_no_duplicate_libs():
    for f in ["operator-errors.sh", "redaction.sh", "validation-logging.sh"]:
        in_root = (ROOT_DIR / "lib" / f).exists()
        in_scripts = (SCRIPTS_LIB / f).exists()
        assert not (in_root and in_scripts), f"DUPLICATE: {f} in both lib/ and scripts/dev/lib/"


def test_no_fragile_relative_paths():
    for sh in Path(ROOT_DIR / "scripts").rglob("*.sh"):
        content = sh.read_text()
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if '$(dirname "$0")' in stripped or "$(dirname $0)" in stripped:
                if stripped.startswith("ROOT_DIR=") or stripped.startswith("SCRIPT_DIR="):
                    continue
                if "BASH_SOURCE" in stripped:
                    continue
                pytest.fail(f"{sh} uses fragile $(dirname $0): {line}")


def test_no_root_lib_references():
    for sh in Path(ROOT_DIR / "scripts").rglob("*.sh"):
        content = sh.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("source ") and "lib/" in line and "scripts/dev/lib/" not in line:
                if "${SCRIPT_DIR}/lib/" in line or "${ROOT_DIR}/scripts/dev/lib/" in line:
                    continue
                if "${ROOT_DIR}/lib/" in line:
                    pytest.fail(f"{sh} references root lib/ instead of scripts/dev/lib/: {line}")


def test_common_sh_loads_operator_errors():
    common_sh = ROOT_DIR / "scripts" / "common.sh"
    content = common_sh.read_text()
    assert "scripts/dev/lib/operator-errors.sh" in content


def test_project_root_sh_function():
    pr_sh = SCRIPTS_LIB / "project-root.sh"
    content = pr_sh.read_text()
    assert "resolve_project_root" in content


def test_redaction_sh_loadable():
    token = "sk-" + "1234567890123456789012345"
    result = subprocess.run(
        [
            "bash",
            "-c",
            f"source {SCRIPTS_LIB / 'redaction.sh'} && echo 'my key is {token}' | redact_stream",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "[REDACTED]" in result.stdout
    assert token not in result.stdout


def test_validation_logging_sh_loadable():
    result = subprocess.run(
        [
            "bash",
            "-c",
            f"source {SCRIPTS_LIB / 'validation-logging.sh'} && log_info 'test message'",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    clean = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    assert "INFO: test message" in clean


def test_operator_errors_sh_loadable():
    result = subprocess.run(
        ["bash", "-c", f"source {SCRIPTS_LIB / 'operator-errors.sh'} && operator_success 'loaded'"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "[SUCCESS]" in result.stdout
