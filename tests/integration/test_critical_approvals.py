import sys
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.core.admin_rbac import AdminAuditEvent
from app.models.governance.human_governance import CriticalApproval
from app.services.approval_service import ApprovalService, approvals_ws_manager
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def reset_all_config_services():
    # Loop over all registered sys.modules to clear cached ConfigService singletons
    for name, mod in list(sys.modules.items()):
        if "config_service" in name and mod:
            if hasattr(mod, "ConfigService"):
                try:
                    mod.ConfigService.reset_instance()
                except Exception:
                    pass


@pytest.fixture(autouse=True)
def setup_critical_approval_env(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "test-topic")
    monkeypatch.setenv("NTFY_URL", "https://ntfy.sh")
    monkeypatch.setenv("GOTIFY_URL", "https://gotify.example.com")
    monkeypatch.setenv("GOTIFY_TOKEN", "test-token")
    monkeypatch.setenv("RBAC_ADMIN_ENABLED", "false")
    monkeypatch.setenv("ADMIN_SUPER_TOKEN", "super-token")
    monkeypatch.setenv("ADMIN_WRITE_TOKEN", "write-token")
    monkeypatch.setenv("ADMIN_READ_TOKEN", "read-token")
    reset_all_config_services()
    get_settings.cache_clear()
    yield
    reset_all_config_services()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_create_and_process_approval(admin_client: AsyncClient, session: AsyncSession):
    # Debug settings
    settings = get_settings()
    print("\n--- DEBUG INFO ---")
    print("admin_write_token:", settings.admin_write_token)
    print("rbac_admin_enabled:", settings.rbac_admin_enabled)
    print("------------------")

    external_calls = []
    original_post = httpx.AsyncClient.post

    async def mock_post_fn(self, url, *args, **kwargs):
        url_str = str(url)
        if "ntfy.sh" in url_str or "gotify.example.com" in url_str:
            external_calls.append(url_str)
            return MagicMock(status_code=200)
        return await original_post(self, url, *args, **kwargs)

    with patch("httpx.AsyncClient.post", autospec=True, side_effect=mock_post_fn):
        # 1. Create approval request via API
        headers = {"X-Admin-Token": "write-token"}
        resp = await admin_client.post(
            "/admin/approvals",
            json={
                "action_type": "model_deletion",
                "description": "Delete model gpt-4-old from registry",
                "payload": {"model_id": "gpt-4-old"},
                "metadata_json": {"requested_by_email": "operator@test.com"},
                "expires_in_seconds": 60,
            },
            headers=headers,
        )
        print("API RESPONSE:", resp.status_code, resp.text)
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_type"] == "model_deletion"
        assert data["status"] == "pending"
        assert data["requested_by"] == "admin"
        req_id = data["id"]

        # Verify notifications were dispatched to ntfy and gotify
        assert len(external_calls) == 2

        # Verify audit event is recorded
        stmt_audit = select(AdminAuditEvent).where(
            AdminAuditEvent.event_type == "critical_approval.created"
        )
        audit_res = await session.execute(stmt_audit)
        created_audit = audit_res.scalar_one_or_none()
        assert created_audit is not None
        assert created_audit.target_id == req_id

        # 2. Get approval request details
        resp_get = await admin_client.get(f"/admin/approvals/{req_id}", headers=headers)
        assert resp_get.status_code == 200
        assert resp_get.json()["status"] == "pending"

        # Reset external calls log
        external_calls.clear()

        # 3. Approve request
        resp_approve = await admin_client.post(
            f"/admin/approvals/{req_id}/approve",
            json={"decision_reason": "Approved for migration"},
            headers=headers,
        )
        assert resp_approve.status_code == 200
        assert resp_approve.json()["status"] == "approved"
        assert resp_approve.json()["decision_reason"] == "Approved for migration"

        # Verify notifications were dispatched on approve
        assert len(external_calls) == 2

        # Verify database state
        stmt_db = select(CriticalApproval).where(CriticalApproval.id == uuid.UUID(req_id))
        db_res = await session.execute(stmt_db)
        req_db = db_res.scalar_one_or_none()
        assert req_db.status == "approved"
        assert req_db.decided_by == "admin"

        # Verify approve audit log
        stmt_audit_app = select(AdminAuditEvent).where(
            AdminAuditEvent.event_type == "critical_approval.approved"
        )
        audit_app_res = await session.execute(stmt_audit_app)
        approved_audit = audit_app_res.scalar_one_or_none()
        assert approved_audit is not None
        assert approved_audit.target_id == req_id


@pytest.mark.asyncio
async def test_reject_approval_request(admin_client: AsyncClient, session: AsyncSession):
    external_calls = []
    original_post = httpx.AsyncClient.post

    async def mock_post_fn(self, url, *args, **kwargs):
        url_str = str(url)
        if "ntfy.sh" in url_str or "gotify.example.com" in url_str:
            external_calls.append(url_str)
            return MagicMock(status_code=200)
        return await original_post(self, url, *args, **kwargs)

    with patch("httpx.AsyncClient.post", autospec=True, side_effect=mock_post_fn):
        # Create request
        headers = {"X-Admin-Token": "write-token"}
        resp = await admin_client.post(
            "/admin/approvals",
            json={"action_type": "bypass_policy", "description": "Bypass safety rate limit"},
            headers=headers,
        )
        req_id = resp.json()["id"]

        # Reject request
        resp_reject = await admin_client.post(
            f"/admin/approvals/{req_id}/reject",
            json={"decision_reason": "Policy bypass is prohibited"},
            headers=headers,
        )
        assert resp_reject.status_code == 200
        assert resp_reject.json()["status"] == "rejected"
        assert resp_reject.json()["decision_reason"] == "Policy bypass is prohibited"

        # Verify database state
        stmt_db = select(CriticalApproval).where(CriticalApproval.id == uuid.UUID(req_id))
        db_res = await session.execute(stmt_db)
        req_db = db_res.scalar_one_or_none()
        assert req_db.status == "rejected"

        # Verify reject audit log
        stmt_audit_rej = select(AdminAuditEvent).where(
            AdminAuditEvent.event_type == "critical_approval.rejected"
        )
        audit_rej_res = await session.execute(stmt_audit_rej)
        rejected_audit = audit_rej_res.scalar_one_or_none()
        assert rejected_audit is not None
        assert rejected_audit.target_id == req_id


@pytest.mark.asyncio
async def test_expired_approval_request(admin_client: AsyncClient, session: AsyncSession):
    external_calls = []
    original_post = httpx.AsyncClient.post

    async def mock_post_fn(self, url, *args, **kwargs):
        url_str = str(url)
        if "ntfy.sh" in url_str or "gotify.example.com" in url_str:
            external_calls.append(url_str)
            return MagicMock(status_code=200)
        return await original_post(self, url, *args, **kwargs)

    with patch("httpx.AsyncClient.post", autospec=True, side_effect=mock_post_fn):
        # 1. Create a request that is already expired
        req = CriticalApproval(
            action_type="delete_key",
            description="Delete admin api key",
            status="pending",
            requested_by="operator",
            requested_at=utc_now() - timedelta(seconds=120),
            expires_at=utc_now() - timedelta(seconds=60),
        )
        session.add(req)
        await session.commit()

        # 2. Check all expirations service-side
        await ApprovalService.check_all_expirations(session)
        await session.refresh(req)
        assert req.status == "expired"

        # Verify expired audit log
        stmt_audit_exp = select(AdminAuditEvent).where(
            AdminAuditEvent.event_type == "critical_approval.expired"
        )
        audit_exp_res = await session.execute(stmt_audit_exp)
        expired_audit = audit_exp_res.scalar_one_or_none()
        assert expired_audit is not None
        assert expired_audit.target_id == str(req.id)


@pytest.mark.asyncio
async def test_websocket_broadcast():
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []
            self.accepted = False

        async def accept(self):
            self.accepted = True

        async def send_json(self, message):
            self.sent_messages.append(message)

    ws = MockWebSocket()
    await approvals_ws_manager.connect(ws)
    assert ws.accepted

    # Broadcast message
    test_msg = {"event": "critical_approval.created", "id": "test-id"}
    await approvals_ws_manager.broadcast(test_msg)
    assert len(ws.sent_messages) == 1
    assert ws.sent_messages[0] == test_msg

    # Disconnect
    approvals_ws_manager.disconnect(ws)
    assert ws not in approvals_ws_manager.active_connections
