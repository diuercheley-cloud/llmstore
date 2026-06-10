import io
import json
import os
import zipfile
from pathlib import Path

TEST_TMP = Path("/tmp/llm-inference-stack-control-plane-tests")
TEST_TMP.mkdir(parents=True, exist_ok=True)
TEST_DB_FILE = TEST_TMP / "plugin-runtime-execution.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.core.admin_rbac import AdminUser  # noqa: F401
from app.models.core.client import Client
from app.models.operations.plugin_runtime import PluginRuntimeExecution
from app.services.operations.plugin_runtime.abi_contracts import PluginABIContractService
from app.services.operations.plugin_runtime.capability_boundaries import (
    PluginCapabilityBoundaryService,
)
from app.services.operations.plugin_runtime.execution_runtime import (
    GovernedPluginRuntime,
    PluginExecutionError,
)
from app.services.operations.plugin_runtime.isolation_policy import PluginIsolationPolicyService
from app.services.plugins.plugin_marketplace import PluginMarketplaceService


def _plugin_zip(source: str, name: str = "runtime-plugin", version: str = "1.0.0") -> bytes:
    manifest = {
        "manifest_version": "1",
        "name": name,
        "version": version,
        "description": "Runtime plugin",
        "author": "tests",
        "license": "MIT",
        "entrypoint": "plugin.py",
        "plugin_type": "ui_extension",
        "permissions": ["read_data"],
        "checksums": {},
        "minimum_platform_version": "1.0.0",
        "compatibility": {"platform": [">=1.0.0"]},
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("plugin.py", source)
    return buf.getvalue()


@pytest_asyncio.fixture(autouse=True)
async def setup_db(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "plugin_signature_required", False)
    monkeypatch.setattr(settings, "pki_enabled", False)
    monkeypatch.setattr(settings, "attestation_mode", "advisory")
    monkeypatch.setattr(settings, "pki_storage_path", str(tmp_path / "pki" / "ca.crt"))

    async with engine.begin() as conn:
        import app.models.core.security_pki  # noqa
        import app.models.core.security_event  # noqa
        import app.models.plugins.marketplace  # noqa
        import app.models.operations.plugin_runtime  # noqa
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session


async def _install_enabled_plugin(db_session, source: str, name: str = "runtime-plugin", version: str = "1.0.0"):
    marketplace = PluginMarketplaceService(db_session)
    install = await marketplace.install_plugin(_plugin_zip(source, name=name, version=version), "plugin.zip")
    await marketplace.enable_plugin(install.id)
    return install


@pytest.mark.asyncio
async def test_governed_plugin_runtime_executes_real_plugin_code(db_session):
    await _install_enabled_plugin(
        db_session,
        "def run(payload):\n    return {'echo': payload['message'], 'length': len(payload['message'])}\n",
    )

    client = Client(name="runtime-client")
    db_session.add(client)
    await db_session.commit()

    contract = PluginABIContractService().create_contract(
        {
            "client_id": client.id,
            "plugin_name": "runtime-plugin",
            "plugin_version": "1.0.0",
            "abi_version": "1.0.0",
            "schema_version": "1.0.0",
            "contract_scope": "workflow",
            "contract_status": "active",
        }
    )
    db_session.add(contract)
    db_session.add(
        PluginIsolationPolicyService().create_default_policy(client.id)
    )
    db_session.add(
        PluginCapabilityBoundaryService().build_boundary(
            {
                "client_id": client.id,
                "abi_contract_id": contract.id,
                "allowed_capabilities_json": ["read_data"],
                "denied_capabilities_json": [],
                "isolation_required": True,
                "offline_only": True,
                "network_allowed": False,
                "subprocess_allowed": False,
                "filesystem_write_allowed": False,
                "external_secret_access_allowed": False,
            }
        )
    )
    await db_session.commit()

    runtime = GovernedPluginRuntime(db_session)
    activation = await runtime.activate(contract)
    execution = await runtime.execute(contract, {"message": "hello"}, activation=activation)
    await db_session.commit()

    assert activation.activation_status == "executed"
    assert execution.execution_status == "completed"
    assert execution.output_payload == {"echo": "hello", "length": 5}


@pytest.mark.asyncio
async def test_governed_plugin_runtime_runs_in_separate_process(db_session):
    await _install_enabled_plugin(
        db_session,
        "import os\ndef run(payload):\n    return {'plugin_pid': os.getpid()}\n",
        name="process-plugin",
    )

    client = Client(name="process-client")
    db_session.add(client)
    await db_session.commit()

    contract = PluginABIContractService().create_contract(
        {
            "client_id": client.id,
            "plugin_name": "process-plugin",
            "plugin_version": "1.0.0",
            "abi_version": "1.0.0",
            "schema_version": "1.0.0",
            "contract_scope": "workflow",
            "contract_status": "active",
        }
    )
    db_session.add(contract)
    db_session.add(PluginIsolationPolicyService().create_default_policy(client.id))
    db_session.add(
        PluginCapabilityBoundaryService().build_boundary(
            {
                "client_id": client.id,
                "abi_contract_id": contract.id,
                "allowed_capabilities_json": ["read_data"],
                "denied_capabilities_json": [],
                "isolation_required": True,
                "offline_only": True,
                "network_allowed": False,
                "subprocess_allowed": False,
                "filesystem_write_allowed": False,
                "external_secret_access_allowed": False,
            }
        )
    )
    await db_session.commit()

    runtime = GovernedPluginRuntime(db_session)
    activation = await runtime.activate(contract)
    execution = await runtime.execute(contract, {}, activation=activation)

    assert execution.runtime_mode == "process_isolated"
    assert execution.output_payload["plugin_pid"] != os.getpid()


@pytest.mark.asyncio
async def test_governed_plugin_runtime_blocks_isolation_violation(db_session):
    await _install_enabled_plugin(
        db_session,
        "def run(payload):\n    return {'ok': True}\n",
        name="restricted-plugin",
    )

    client = Client(name="restricted-client")
    db_session.add(client)
    await db_session.commit()

    contract = PluginABIContractService().create_contract(
        {
            "client_id": client.id,
            "plugin_name": "restricted-plugin",
            "plugin_version": "1.0.0",
            "abi_version": "1.0.0",
            "schema_version": "1.0.0",
            "contract_scope": "workflow",
            "contract_status": "active",
        }
    )
    db_session.add(contract)
    db_session.add(PluginIsolationPolicyService().create_default_policy(client.id))
    db_session.add(
        PluginCapabilityBoundaryService().build_boundary(
            {
                "client_id": client.id,
                "abi_contract_id": contract.id,
                "allowed_capabilities_json": ["read_data", "network"],
                "denied_capabilities_json": [],
                "isolation_required": True,
                "offline_only": False,
                "network_allowed": True,
                "subprocess_allowed": False,
                "filesystem_write_allowed": False,
                "external_secret_access_allowed": False,
            }
        )
    )
    await db_session.commit()

    runtime = GovernedPluginRuntime(db_session)
    activation = await runtime.activate(contract)
    with pytest.raises(PluginExecutionError, match="network access"):
        await runtime.execute(contract, {"message": "blocked"}, activation=activation)

    rows = (await db_session.execute(select(PluginRuntimeExecution))).scalars().all()
    assert rows[-1].execution_status == "failed"


from sqlalchemy import select
