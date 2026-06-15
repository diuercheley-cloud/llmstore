import uuid
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_model_hot_swap_flow(e2e_client, admin_headers):
    model_id = uuid.uuid4()
    backend_id = uuid.uuid4()

    fake_process = MagicMock()
    fake_process.poll.return_value = None
    fake_process.pid = 12345

    with (
        patch("subprocess.Popen", return_value=fake_process) as mock_popen,
        patch("pathlib.Path.exists", return_value=True),
        patch(
            "app.services.model_runtime_manager.ModelRuntimeManager.get_model_health",
            return_value={"status": "ready"},
        ),
        patch(
            "app.services.model_runtime_manager.ModelRuntimeManager._monitor_instance",
            return_value=None,
        ),
    ):
        # 1. Carregar modelo v1
        resp = await e2e_client.post(
            "/admin/models/runtime/load",
            json={
                "model_id": str(model_id),
                "backend_id": str(backend_id),
                "model_path": "/tmp/test-v1.gguf",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        resp_data = resp.json()
        instance_v1_uuid = uuid.UUID(resp_data["id"])
        instance_v1_str = resp_data["id"]

        # Force status to "ready" via DB so activate can proceed
        from app.db.session import get_db_session as _session_factory
        from app.models.operations.model_runtime import ModelRuntimeInstance
        from sqlalchemy import update as sa_update

        async for sess in _session_factory():
            await sess.execute(
                sa_update(ModelRuntimeInstance)
                .where(ModelRuntimeInstance.id == instance_v1_uuid)
                .values(status="ready")
            )
            await sess.commit()
            break

        # 2. Ativar modelo v1
        resp = await e2e_client.post(
            f"/admin/models/runtime/activate/{instance_v1_str}", headers=admin_headers
        )
        assert resp.status_code == 200, f"Activate v1 failed: {resp.text}"

        # 3. Carregar modelo v2
        resp = await e2e_client.post(
            "/admin/models/runtime/load",
            json={
                "model_id": str(model_id),
                "backend_id": str(backend_id),
                "model_path": "/tmp/test-v2.gguf",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        resp_data2 = resp.json()
        instance_v2_uuid = uuid.UUID(resp_data2["id"])
        instance_v2_str = resp_data2["id"]

        # Force v2 to ready
        async for sess in _session_factory():
            await sess.execute(
                sa_update(ModelRuntimeInstance)
                .where(ModelRuntimeInstance.id == instance_v2_uuid)
                .values(status="ready")
            )
            await sess.commit()
            break

        # 4. Ativar v2 (Swap do v1 para o v2)
        resp = await e2e_client.post(
            f"/admin/models/runtime/activate/{instance_v2_str}", headers=admin_headers
        )
        assert resp.status_code == 200, f"Activate v2 failed: {resp.text}"

        # 5. Simular rollback para v1 (model_id e backend_id são query params)
        resp = await e2e_client.post(
            f"/admin/models/runtime/rollback?model_id={model_id}&backend_id={backend_id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200, f"Rollback failed: {resp.text}"

        # 6. Validar estado final
        list_resp = await e2e_client.get("/admin/models/runtime", headers=admin_headers)
        instances = list_resp.json()
        v1_instance = next(i for i in instances if i["id"] == instance_v1_str)
        assert v1_instance["is_active"] is True, f"v1 should be active: {v1_instance}"
        v2_instance = next(i for i in instances if i["id"] == instance_v2_str)
        assert v2_instance["is_active"] is False, f"v2 should be inactive: {v2_instance}"
