import os
import re
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT_DIR / "scripts"

_RESOLVABLE_VARS = {"ROOT_DIR", "SCRIPT_DIR", "PROJECT_ROOT", "script_dir"}


def _shell_scripts():
    for f in sorted(SCRIPTS_DIR.rglob("*.sh")):
        if "__pycache__" not in str(f):
            yield f


def _is_dynamic_source(line):
    if "$(" in line:
        return True
    m = re.search(r'source\s+["\']?\$\{(\w+)\}', line)
    if m and m.group(1) not in _RESOLVABLE_VARS:
        return True
    m = re.search(r'source\s+["\']?\$(\w+)', line)
    if m and m.group(1) not in _RESOLVABLE_VARS:
        return True
    if re.search(r'source\s+["\']?\$\{', line):
        after = re.split(r"\s+", line, maxsplit=1)[1].strip('"').strip("'")
        if after.startswith("${") and after.endswith("}"):
            var = after[2:-1]
            if var not in _RESOLVABLE_VARS:
                return True
    return False


def test_all_scripts_have_valid_shebang():
    for sh in _shell_scripts():
        content = sh.read_text()
        first_line = content.splitlines()[0] if content else ""
        assert first_line in (
            "#!/usr/bin/env bash",
            "#!/bin/bash",
            "#!/bin/sh",
        ), f"{sh}: invalid shebang: {first_line!r}"


def test_all_scripts_executable():
    for sh in _shell_scripts():
        assert os.access(sh, os.X_OK), f"{sh} is not executable"


def test_all_source_targets_exist():
    for sh in _shell_scripts():
        content = sh.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("#") or not line.startswith("source "):
                continue
            if _is_dynamic_source(line):
                continue
            m = re.match(r'source\s+["\']?([^"\'\s]+)["\']?', line)
            if not m:
                continue
            raw = m.group(1)
            resolved = None
            if raw.startswith("/"):
                resolved = Path(raw)
            elif "${ROOT_DIR}" in raw:
                resolved = ROOT_DIR / raw.replace("${ROOT_DIR}/", "")
            elif "${SCRIPT_DIR}" in raw:
                tail = raw.replace("${SCRIPT_DIR}/", "")
                resolved = (sh.resolve().parent / tail).resolve()
            elif "${PROJECT_ROOT}" in raw:
                resolved = ROOT_DIR / raw.replace("${PROJECT_ROOT}/", "")
            else:
                resolved = sh.parent / raw
            if resolved is not None:
                resolved = resolved.resolve()
            # Skip runtime-generated paths (virtualenv, .local, etc.)
            if not resolved.exists():
                if ".venv" in str(resolved) or ".local" in str(resolved):
                    continue
            assert resolved.exists(), f"{sh}: source target not found: {raw} (resolved: {resolved})"


def test_all_bash_n_pass():
    for sh in _shell_scripts():
        result = subprocess.run(["bash", "-n", str(sh)], capture_output=True, text=True)
        assert result.returncode == 0, f"bash -n failed on {sh}:\n{result.stderr}"


def test_py_compile_scripts():
    for py in sorted(SCRIPTS_DIR.glob("*.py")):
        if py.name == "__init__.py":
            continue
        result = subprocess.run(
            ["python3", "-m", "py_compile", str(py)], capture_output=True, text=True
        )
        assert result.returncode == 0, f"py_compile failed on {py}:\n{result.stderr}"
