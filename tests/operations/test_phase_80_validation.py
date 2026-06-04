from pathlib import Path

import sqlalchemy as sa

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "control_plane" / "alembic" / "versions" / "phase80_plugin_supply_chain_provenance_sbom.py"


def test_phase_80_validation_script_present():
    content = (ROOT / "scripts" / "validate_phase_80_plugin_supply_chain.py").read_text(encoding="utf-8")
    assert "Phase 80 plugin supply-chain validation passed." in content
    assert "placeholder SBOM only" in content


def test_phase_80_migration_uses_sqlite_fallback_helpers():
    namespace: dict[str, object] = {}
    exec(MIGRATION_PATH.read_text(encoding="utf-8"), namespace)

    class _Bind:
        class dialect:
            name = "sqlite"

    namespace["op"].get_bind = lambda: _Bind()
    assert isinstance(namespace["_json_type"](), sa.JSON)
    assert isinstance(namespace["_uuid_type"](), sa.String)
