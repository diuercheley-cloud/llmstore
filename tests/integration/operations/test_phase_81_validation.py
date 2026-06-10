from pathlib import Path

import sqlalchemy as sa

from scripts.validate_phase_81_reproducible_builds import validate

ROOT = Path(__file__).resolve().parents[3]
MIGRATION_PATH = ROOT / "control_plane" / "alembic" / "versions" / "phase81_reproducible_build_artifact_verification.py"


def test_phase_81_validation_script_present():
    content = (ROOT / "scripts" / "validate_phase_81_reproducible_builds.py").read_text(encoding="utf-8")
    assert "Phase 81 reproducible build validation passed." in content
    assert "offline-first reproducible build framework" in (ROOT / "control_plane" / "app" / "static" / "admin" / "index.html").read_text(encoding="utf-8")


def test_phase_81_validation_script_has_no_failures():
    assert validate() == []


def test_phase_81_migration_uses_sqlite_fallback_helpers():
    namespace: dict[str, object] = {}
    exec(MIGRATION_PATH.read_text(encoding="utf-8"), namespace)

    class _Bind:
        class dialect:
            name = "sqlite"

    namespace["op"].get_bind = lambda: _Bind()
    assert isinstance(namespace["_json_type"](), sa.JSON)
    assert isinstance(namespace["_uuid_type"](), sa.String)
