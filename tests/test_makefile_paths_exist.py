import re
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
MAKEFILE = ROOT_DIR / "Makefile"


def _makefile_script_refs():
    """Yield all ./scripts/... references found in Makefile"""
    if not MAKEFILE.exists():
        return
    content = MAKEFILE.read_text()
    for m in re.finditer(r'\./scripts/([a-zA-Z0-9_.-]+\.sh)', content):
        yield m.group(1)


def test_makefile_exists():
    assert MAKEFILE.exists()


def test_all_makefile_script_refs_exist():
    missing = []
    for ref in _makefile_script_refs():
        script_path = ROOT_DIR / "scripts" / ref
        if not script_path.exists():
            missing.append(ref)
    assert not missing, f"Makefile references missing scripts:\n" + "\n".join(missing)


def test_all_makefile_script_refs_executable():
    not_exec = []
    for ref in _makefile_script_refs():
        script_path = ROOT_DIR / "scripts" / ref
        if script_path.exists() and not script_path.stat().st_mode & 0o111:
            not_exec.append(ref)
    assert not not_exec, f"Makefile scripts not executable:\n" + "\n".join(not_exec)
