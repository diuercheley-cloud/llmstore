from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / "control_plane" / "alembic" / "versions" / "20260515_phase56_workflow_policy_enforcement.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("phase56_sqlite", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_phase56_sqlite_helpers_use_fallback_types():
    module = _load_module()

    class _Bind:
        class dialect:
            name = "sqlite"

    module.op.get_bind = lambda: _Bind()

    assert isinstance(module._json_type(), sa.JSON)
    assert isinstance(module._uuid_type(), sa.String)


def test_phase56_sqlite_migration_has_tenant_scoped_indexes():
    content = MIGRATION_PATH.read_text()
    assert "tenant_id" in content
    assert "ix_comm_workflow_gov_events_tenant_type" in content
    assert "ix_comm_workflow_replay_sessions_tenant_status" in content
