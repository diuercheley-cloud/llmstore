#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

required_files=(
  "control_plane/app.models.commercial.commercial_sovereign_governance.py"
  "control_plane/app/services/governance/airgap_sync.py"
  "control_plane/app/services/security/offline_crl.py"
  "control_plane/app/services/security/hardware_attestation.py"
  "control_plane/app/api/commercial_sovereign_governance_admin.py"
  "docs/SOVEREIGN_AIRGAP_GOVERNANCE.md"
)

for file in "${required_files[@]}"; do
  [[ -f "$file" ]] || { echo "missing required file: $file"; exit 1; }
done

PYTHON_BIN="${ROOT_DIR}/venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

"${PYTHON_BIN}" - <<'PY'
import asyncio
import os
import sys
import uuid
from pathlib import Path

ROOT = Path.cwd()
CONTROL_PLANE = ROOT / "control_plane"
if str(CONTROL_PLANE) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE))

os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/sovereign-airgap-validate.db")
os.environ.setdefault("REDIS_URL", "redis://test.invalid:6379/0")
os.environ.setdefault("DATA_PLANE_BASE_URL", "http://localhost:8081")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.services.governance.airgap_sync import create_airgap_package, export_airgap_package, import_airgap_package, verify_airgap_manifest
from app.services.security.hardware_attestation import collect_attestation_placeholder
from app.services.security.offline_crl import apply_offline_crl, create_offline_crl


async def main():
    engine = create_async_engine(os.environ["DATABASE_URL"])
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_local() as session:
        package = await create_airgap_package(
            session,
            package_type="policy_bundle",
            payload={"classification": "sovereign_restricted", "api_key": "should-not-leak"},
            source_cluster_id="cluster-a",
            package_version="37.0",
            classification="sovereign_restricted",
            chain_of_custody_json={"events": [{"actor": "ops", "action": "sealed", "timestamp": "2026-05-15T00:00:00Z"}]},
        )
        bundle = await export_airgap_package(
            session,
            package.id,
            payload={"classification": "sovereign_restricted", "api_key": "should-not-leak"},
            classification="sovereign_restricted",
        )
        verification = await verify_airgap_manifest(session, bundle)
        assert verification["valid"], verification
        await import_airgap_package(session, bundle)

        crl = await create_offline_crl(
            session,
            crl_version="37.0",
            revoked_bundle_hashes_json=[bundle["files"]["manifest.json"]["manifest_hash"]],
        )
        await apply_offline_crl(session, crl.id)

        attestation = await collect_attestation_placeholder(
            session,
            cluster_id="cluster-a",
            node_id="node-1",
            evidence_json={"boot": "placeholder"},
            status="trusted",
        )
        assert attestation.evidence_hash

        payload_blob = str(bundle["files"].get("payload.json", "")) + str(bundle["files"].get("payload.enc", ""))
        assert "should-not-leak" not in payload_blob
        await session.commit()

    await engine.dispose()


asyncio.run(main())
PY

echo "sovereign airgap governance validation completed"
