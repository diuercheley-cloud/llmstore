import io
import json
import logging
import os
import subprocess
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.operations.plugin_runtime import (
    DeterministicExtensionLoadPlan,
    PluginABIContract,
    PluginCapabilityBoundary,
    PluginIsolationPolicy,
    PluginLifecycleEvent,
    PluginRuntimeActivation,
    PluginRuntimeExecution,
)
from app.models.plugins.marketplace import PluginInstall, PluginMarketplaceEntry, PluginVersion
from app.services.agents.tool_sandbox import execute_in_sandbox
from app.services.operations.plugin_runtime.hash_utils import sha256_hex

logger = logging.getLogger(__name__)


class PluginExecutionError(RuntimeError):
    pass


class GovernedPluginRuntime:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def activate(
        self,
        contract: PluginABIContract,
        load_plan: DeterministicExtensionLoadPlan | None = None,
    ) -> PluginRuntimeActivation:
        install, version = await self._resolve_install(contract)
        activation = PluginRuntimeActivation(
            id=sha256_hex(
                {
                    "kind": "plugin_runtime_activation_id",
                    "client_id": str(contract.client_id),
                    "abi_contract_id": contract.id,
                    "install_path": install.install_path,
                }
            ),
            client_id=contract.client_id,
            abi_contract_id=contract.id,
            load_plan_id=load_plan.id if load_plan else None,
            activation_status="active",
            runtime_mode="process_isolated",
            artifact_locator=json.dumps(
                {
                    "install_path": install.install_path,
                    "version": version.version,
                    "entrypoint": version.manifest_json.get("entrypoint", "plugin.py"),
                },
                sort_keys=True,
            ),
            immutable_hash=sha256_hex(
                {
                    "kind": "plugin_runtime_activation",
                    "client_id": str(contract.client_id),
                    "abi_contract_id": contract.id,
                    "load_plan_id": load_plan.id if load_plan else None,
                    "install_path": install.install_path,
                }
            ),
        )
        self.db.add(activation)
        self.db.add(
            PluginLifecycleEvent(
                id=sha256_hex(
                    {
                        "kind": "plugin_lifecycle_event_id",
                        "client_id": str(contract.client_id),
                        "abi_contract_id": contract.id,
                        "lifecycle_event_type": "activated",
                        "activation_id": activation.id,
                    }
                ),
                client_id=contract.client_id,
                abi_contract_id=contract.id,
                lifecycle_event_type="activated",
                lifecycle_status="accepted",
                reason="sandboxed plugin runtime activated with real local artifact",
                immutable_hash=sha256_hex(
                    {
                        "kind": "plugin_lifecycle_event",
                        "client_id": str(contract.client_id),
                        "abi_contract_id": contract.id,
                        "lifecycle_event_type": "activated",
                        "activation_id": activation.id,
                    }
                ),
            )
        )
        await self.db.flush()
        return activation

    async def execute(
        self,
        contract: PluginABIContract,
        payload: dict[str, Any],
        activation: PluginRuntimeActivation | None = None,
        timeout_seconds: int = 30,
    ) -> PluginRuntimeExecution:
        install, version = await self._resolve_install(contract)
        boundary = await self._resolve_boundary(contract)
        policy = await self._resolve_policy(contract)
        entrypoint = version.manifest_json.get("entrypoint", "plugin.py")

        execution = PluginRuntimeExecution(
            id=sha256_hex(
                {
                    "kind": "plugin_runtime_execution_id",
                    "client_id": str(contract.client_id),
                    "abi_contract_id": contract.id,
                    "payload": payload,
                    "started_at": utc_now().isoformat(),
                }
            ),
            client_id=contract.client_id,
            abi_contract_id=contract.id,
            activation_id=activation.id if activation else None,
            execution_status="running",
            runtime_mode="process_isolated",
            input_payload=payload,
            immutable_hash=sha256_hex(
                {
                    "kind": "plugin_runtime_execution",
                    "client_id": str(contract.client_id),
                    "abi_contract_id": contract.id,
                    "payload": payload,
                }
            ),
        )
        self.db.add(execution)
        await self.db.flush()
        try:
            self._enforce_isolation(boundary, policy)
        except Exception as exc:
            execution.execution_status = "failed"
            execution.error_message = str(exc)
            execution.completed_at = utc_now()
            await self.db.flush()
            raise

        module_callable = self._build_callable(install.install_path, entrypoint)
        try:
            output = await execute_in_sandbox(
                db=self.db,
                tenant_id=str(contract.client_id),
                invocation_id=uuid.uuid5(uuid.NAMESPACE_URL, execution.id),
                tool_name=contract.plugin_name,
                tool_category="plugin_runtime",
                parameters={"payload": payload, "command": "plugin_run"},
                allowed_commands=["plugin_run"],
                timeout_seconds=timeout_seconds,
                tool_callable=module_callable,
                sandbox_type="plugin_runtime",
            )
            if not isinstance(output, dict):
                output = {"result": output}
            execution.output_payload = output
            execution.output_hash = sha256_hex(output)
            execution.execution_status = "completed"
            execution.completed_at = utc_now()
            if activation is not None:
                activation.activation_status = "executed"
                activation.updated_at = utc_now()
            self.db.add(
                PluginLifecycleEvent(
                    id=sha256_hex(
                        {
                            "kind": "plugin_lifecycle_event_id",
                            "client_id": str(contract.client_id),
                            "abi_contract_id": contract.id,
                            "lifecycle_event_type": "executed",
                            "execution_id": execution.id,
                        }
                    ),
                    client_id=contract.client_id,
                    abi_contract_id=contract.id,
                    lifecycle_event_type="executed",
                    lifecycle_status="accepted",
                    reason="sandboxed plugin runtime executed local plugin artifact",
                    immutable_hash=sha256_hex(
                        {
                            "kind": "plugin_lifecycle_event",
                            "client_id": str(contract.client_id),
                            "abi_contract_id": contract.id,
                            "lifecycle_event_type": "executed",
                            "execution_id": execution.id,
                        }
                    ),
                )
            )
            await self.db.flush()
            return execution
        except Exception as exc:
            execution.execution_status = "failed"
            execution.error_message = str(exc)
            execution.completed_at = utc_now()
            await self.db.flush()
            raise

    async def _resolve_install(self, contract: PluginABIContract) -> tuple[PluginInstall, PluginVersion]:
        result = await self.db.execute(
            select(PluginInstall, PluginVersion)
            .join(PluginVersion, PluginVersion.id == PluginInstall.current_version_id)
            .join(PluginMarketplaceEntry, PluginMarketplaceEntry.id == PluginInstall.plugin_entry_id)
            .where(
                PluginMarketplaceEntry.name == contract.plugin_name,
                PluginVersion.version == contract.plugin_version,
                PluginInstall.is_enabled.is_(True),
            )
        )
        row = result.first()
        if row is None:
            raise PluginExecutionError(
                f"Enabled installed plugin artifact not found for {contract.plugin_name} v{contract.plugin_version}"
            )
        return row[0], row[1]

    async def _resolve_boundary(self, contract: PluginABIContract) -> PluginCapabilityBoundary:
        result = await self.db.execute(
            select(PluginCapabilityBoundary)
            .where(PluginCapabilityBoundary.abi_contract_id == contract.id)
            .order_by(PluginCapabilityBoundary.created_at.desc())
        )
        boundary = result.scalars().first()
        if boundary is None:
            raise PluginExecutionError("Capability boundary is required before plugin activation")
        return boundary

    async def _resolve_policy(self, contract: PluginABIContract) -> PluginIsolationPolicy:
        result = await self.db.execute(
            select(PluginIsolationPolicy)
            .where(PluginIsolationPolicy.client_id == contract.client_id)
            .order_by(PluginIsolationPolicy.created_at.desc())
        )
        policy = result.scalars().first()
        if policy is None:
            raise PluginExecutionError("Isolation policy is required before plugin activation")
        return policy

    def _enforce_isolation(self, boundary: PluginCapabilityBoundary, policy: PluginIsolationPolicy) -> None:
        if boundary.network_allowed and policy.deny_network:
            raise PluginExecutionError("Isolation policy blocks network access for plugin runtime")
        if boundary.subprocess_allowed and policy.deny_subprocess:
            raise PluginExecutionError("Isolation policy blocks subprocess access for plugin runtime")
        if boundary.filesystem_write_allowed and policy.deny_external_filesystem_write:
            raise PluginExecutionError("Isolation policy blocks filesystem writes for plugin runtime")
        if boundary.external_secret_access_allowed and policy.deny_plaintext_secret_access:
            raise PluginExecutionError("Isolation policy blocks plaintext secret access for plugin runtime")

    def _build_callable(self, install_path: str, entrypoint: str):
        def run_plugin(*, payload: dict[str, Any], command: str | None = None):
            install_dir = Path(install_path)
            archives = sorted(install_dir.glob("*.zip"))
            if not archives:
                raise PluginExecutionError(f"No plugin archive found in {install_dir}")

            archive = archives[-1]
            workdir = Path(tempfile.mkdtemp(prefix="plugin-runtime-"))
            try:
                with zipfile.ZipFile(io.BytesIO(archive.read_bytes())) as zf:
                    zf.extractall(workdir)
                entrypoint_path = workdir / entrypoint
                if not entrypoint_path.exists():
                    raise PluginExecutionError(f"Entrypoint '{entrypoint}' not found in plugin archive")

                code = entrypoint_path.read_text(encoding="utf-8")
                self._validate_source(code)
                runner_path = workdir / "_plugin_runtime_runner.py"
                runner_path.write_text(
                    """
import importlib.util
import json
import sys
from pathlib import Path

entrypoint = Path(sys.argv[1])
payload = json.loads(sys.argv[2])
spec = importlib.util.spec_from_file_location("plugin_runtime_module", entrypoint)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to create plugin import spec")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if not hasattr(module, "run") or not callable(module.run):
    raise RuntimeError("Plugin entrypoint must expose callable 'run(payload)'")
result = module.run(payload)
if not isinstance(result, dict):
    result = {"result": result}
print(json.dumps(result))
""".strip(),
                    encoding="utf-8",
                )
                env = {
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONNOUSERSITE": "1",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONPATH": "",
                    "HOME": str(workdir),
                }
                proc = subprocess.run(
                    [
                        "python3",
                        "-I",
                        str(runner_path),
                        str(entrypoint_path),
                        json.dumps(payload, sort_keys=True),
                    ],
                    cwd=str(workdir),
                    capture_output=True,
                    text=True,
                    timeout=20,
                    env=env,
                )
                if proc.returncode != 0:
                    stderr = (proc.stderr or "").strip()
                    raise PluginExecutionError(stderr or "Plugin subprocess execution failed")
                stdout = (proc.stdout or "").strip()
                if not stdout:
                    return {"status": "success"}
                return json.loads(stdout)
            finally:
                shutil.rmtree(workdir, ignore_errors=True)

        return run_plugin

    def _validate_source(self, source: str) -> None:
        blocked_markers = [
            "import subprocess",
            "from subprocess",
            "import socket",
            "from socket",
            "os.system(", # nosec
            "subprocess.",
        ]
        for marker in blocked_markers:
            if marker in source:
                raise PluginExecutionError(f"Plugin source violates isolation rule: {marker}")
