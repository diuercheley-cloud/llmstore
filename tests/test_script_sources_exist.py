import os
import re
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent


def _shell_scripts():
    for f in sorted((ROOT_DIR / "scripts").rglob("*.sh")):
        if "__pycache__" not in str(f):
            yield f


_RESOLVABLE_VARS = {"ROOT_DIR", "SCRIPT_DIR", "PROJECT_ROOT", "script_dir"}


def _resolve(path_str, script_path):
    path_str = path_str.strip('"').strip("'")
    root = ROOT_DIR
    if "${ROOT_DIR}" in path_str:
        return root / path_str.replace("${ROOT_DIR}/", "")
    if "${SCRIPT_DIR}" in path_str:
        return root / "scripts" / path_str.replace("${SCRIPT_DIR}/", "")
    if "${PROJECT_ROOT}" in path_str:
        return root / path_str.replace("${PROJECT_ROOT}/", "")
    if "${script_dir}" in path_str:
        return root / "scripts" / path_str.replace("${script_dir}/", "")
    if path_str.startswith("/"):
        return Path(path_str)
    return (script_path.parent / path_str).resolve()


def _is_dynamic_source(line):
    """Check if a source line uses runtime-only paths."""
    if "$(" in line:
        return True
    m = re.search(r'source\s+["\']?\$\{(\w+)\}', line)
    if m and m.group(1) not in _RESOLVABLE_VARS:
        return True
    m = re.search(r'source\s+["\']?\$(\w+)', line)
    if m and m.group(1) not in _RESOLVABLE_VARS:
        return True
    if re.search(r'source\s+["\']?\$\{', line):
        # Check if the entire target after 'source' is just a variable
        after = re.split(r'\s+', line, maxsplit=1)[1].strip('"').strip("'")
        if after.startswith("${") and after.endswith("}"):
            var = after[2:-1]
            if var not in _RESOLVABLE_VARS:
                return True
    return False


def _is_runtime_generated(path):
    """Check if a path points to a runtime-generated location."""
    path_str = str(path)
    return ".venv" in path_str or ".local" in path_str or path_str.endswith("/activate")


def test_all_sources_exist():
    missing = []
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
            src = m.group(1)
            resolved = _resolve(src, sh)
            if not resolved.exists() and not _is_runtime_generated(resolved):
                missing.append(f"{sh}: {src} -> {resolved}")
    assert not missing, "\n".join(missing)


def test_sources_use_scripts_lib_not_root_lib():
    for sh in _shell_scripts():
        content = sh.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("source ") and "lib/" in line:
                if "${ROOT_DIR}/lib/" in line and "${ROOT_DIR}/scripts/lib/" not in line:
                    assert False, f"{sh}: still references ROOT_DIR/lib/: {line}"


def test_no_fragile_source():
    for sh in _shell_scripts():
        content = sh.read_text()
        for line in content.splitlines():
            if '$(dirname "$0")' in line or '$(dirname $0)' in line:
                if '$(dirname "${BASH_SOURCE[0]}")' in line:
                    continue
                rel = sh.relative_to(ROOT_DIR)
                assert "${BASH_SOURCE[0]}" in content or "${BASH_SOURCE[0]}" in line, (
                    f"{rel}: uses legacy dirname \$0 without BASH_SOURCE"
                )


def test_common_sh_sources():
    common_sh = ROOT_DIR / "scripts" / "common.sh"
    assert common_sh.exists()
    content = common_sh.read_text()
    assert "scripts/lib/operator-errors.sh" in content
    assert "${ROOT_DIR}" in content


def test_audit_script_runs():
    result = subprocess.run(
        [str(ROOT_DIR / "scripts" / "audit-shell-lib-layout.sh")],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"audit script failed:\n{result.stderr}\n{result.stdout}"
