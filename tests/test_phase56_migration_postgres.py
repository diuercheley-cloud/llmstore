from __future__ import annotations

import importlib.util
from pathlib import Path

from sqlalchemy.dialects import postgresql


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / "control_plane" / "alembic" / "versions" / "20260515_phase56_workflow_policy_enforcement.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("phase56_postgres", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_phase56_postgres_helpers_use_native_types():
    module = _load_module()

    class _Bind:
        class dialect:
            name = "postgresql"

    module.op.get_bind = lambda: _Bind()

    assert isinstance(module._json_type(), postgresql.JSONB)
    assert isinstance(module._uuid_type(), postgresql.UUID)


def test_phase56_postgres_migration_tracks_phase55_branch():
    module = _load_module()
    assert module.down_revision == "20260515_phase55"
    assert module.revision == "20260515_phase56"
