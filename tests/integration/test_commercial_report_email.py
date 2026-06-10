import ssl
from datetime import datetime, timedelta, timezone

import pytest
from app.core.config import get_settings
from app.models.commercial.commercial_report_delivery_log import CommercialReportDeliveryLog
from app.services.routing.commercial_report_email import (
    SecurityScanError,
    retry_send_with_backoff,
    sanitize_email_payload,
)
from app.services.routing.commercial_report_export import CommercialReportExportService
from fastapi import HTTPException
from sqlalchemy import select


class FakeSMTP:
    sent_messages = []
    login_calls = 0
    starttls_calls = 0

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def ehlo(self):
        return None

    def starttls(self, context=None):
        type(self).starttls_calls += 1
        return None

    def login(self, username, password):
        type(self).login_calls += 1
        return None

    def send_message(self, message, to_addrs=None):
        type(self).sent_messages.append({"message": message, "to_addrs": list(to_addrs or [])})
        return {}


class FakeSMTPAuthFailure(FakeSMTP):
    def login(self, username, password):
        raise __import__("smtplib").SMTPAuthenticationError(535, b"bad auth")


class FakeSMTPTLSFailure(FakeSMTP):
    def starttls(self, context=None):
        raise ssl.SSLError("tls broken")


@pytest.mark.asyncio
async def test_disabled_mode_creates_blocked_delivery_log(session, monkeypatch):
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ENABLED", "false")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MODE", "disabled")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ALLOWLIST", "ops@example.com")
    get_settings.cache_clear()

    service = CommercialReportExportService(session)
    schedule = await service.create_schedule(
        {
            "name": "Disabled Mode",
            "frequency": "monthly",
            "day_of_month": 1,
            "recipients_json": ["ops@example.com"],
            "format": "html",
        },
        actor="admin@example.com",
    )
    result = await service.run_schedule_now(schedule.id)

    assert result["status"] == "email_disabled"
    delivery = (await session.execute(select(CommercialReportDeliveryLog))).scalar_one()
    assert delivery.delivery_status == "blocked"
    assert delivery.error_message == "email_disabled: SMTP delivery is disabled"


@pytest.mark.asyncio
async def test_dry_run_logs_without_real_send(session, monkeypatch):
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MODE", "dry_run")
    monkeypatch.setenv("COMMERCIAL_REPORT_SEND_REAL_EMAIL", "false")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ALLOWLIST", "ops@example.com")
    get_settings.cache_clear()

    service = CommercialReportExportService(session)
    schedule = await service.create_schedule(
        {
            "name": "Dry Run",
            "frequency": "weekly",
            "day_of_week": 1,
            "recipients_json": ["ops@example.com"],
            "format": "json",
        },
        actor="admin@example.com",
    )
    result = await service.run_schedule_now(schedule.id)

    assert result["status"] == "would_send"
    delivery = (await session.execute(select(CommercialReportDeliveryLog))).scalar_one()
    assert delivery.delivery_status == "dry_run"
    assert delivery.delivery_mode == "dry_run"


@pytest.mark.asyncio
async def test_smtp_mode_mocked_send(session, monkeypatch):
    import app.services.routing.commercial_report_email as email_mod

    FakeSMTP.sent_messages = []
    FakeSMTP.login_calls = 0
    FakeSMTP.starttls_calls = 0
    monkeypatch.setattr(email_mod.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MODE", "smtp")
    monkeypatch.setenv("COMMERCIAL_REPORT_SEND_REAL_EMAIL", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_PORT", "587")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_USERNAME", "user")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_PASSWORD", "secret-password")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_FROM", "reports@example.com")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ALLOWLIST", "ops@example.com")
    get_settings.cache_clear()

    service = CommercialReportExportService(session)
    schedule = await service.create_schedule(
        {
            "name": "SMTP Send",
            "frequency": "weekly",
            "day_of_week": 1,
            "recipients_json": ["ops@example.com"],
            "format": "html",
        },
        actor="admin@example.com",
    )
    result = await service.run_schedule_now(schedule.id)

    assert result["status"] == "sent"
    assert FakeSMTP.starttls_calls == 1
    assert FakeSMTP.login_calls == 1
    assert FakeSMTP.sent_messages[0]["to_addrs"] == ["ops@example.com"]
    delivery = (await session.execute(select(CommercialReportDeliveryLog))).scalar_one()
    assert delivery.delivery_status == "sent"
    assert delivery.smtp_host == "s***.example.com"


@pytest.mark.asyncio
async def test_auth_failure_logged(session, monkeypatch):
    import app.services.routing.commercial_report_email as email_mod

    monkeypatch.setattr(email_mod.smtplib, "SMTP", FakeSMTPAuthFailure)
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MODE", "smtp")
    monkeypatch.setenv("COMMERCIAL_REPORT_SEND_REAL_EMAIL", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_FROM", "reports@example.com")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_USERNAME", "user")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_PASSWORD", "wrong")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ALLOWLIST", "ops@example.com")
    get_settings.cache_clear()

    service = CommercialReportExportService(session)
    schedule = await service.create_schedule(
        {"name": "Auth Failure", "frequency": "weekly", "day_of_week": 1, "recipients_json": ["ops@example.com"]},
        actor="admin@example.com",
    )
    with pytest.raises(HTTPException) as exc:
        await service.run_schedule_now(schedule.id)
    assert exc.value.status_code == 502

    delivery = (await session.execute(select(CommercialReportDeliveryLog))).scalar_one()
    assert delivery.delivery_status == "failed"
    assert delivery.error_message == "auth_failure: SMTP authentication failed"


@pytest.mark.asyncio
async def test_tls_failure_logged(session, monkeypatch):
    import app.services.routing.commercial_report_email as email_mod

    monkeypatch.setattr(email_mod.smtplib, "SMTP", FakeSMTPTLSFailure)
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MODE", "smtp")
    monkeypatch.setenv("COMMERCIAL_REPORT_SEND_REAL_EMAIL", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_FROM", "reports@example.com")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ALLOWLIST", "ops@example.com")
    get_settings.cache_clear()

    service = CommercialReportExportService(session)
    schedule = await service.create_schedule(
        {"name": "TLS Failure", "frequency": "weekly", "day_of_week": 1, "recipients_json": ["ops@example.com"]},
        actor="admin@example.com",
    )
    with pytest.raises(HTTPException) as exc:
        await service.run_schedule_now(schedule.id)
    assert exc.value.status_code == 502

    delivery = (await session.execute(select(CommercialReportDeliveryLog))).scalar_one()
    assert delivery.delivery_status == "failed"
    assert delivery.error_message == "tls_failure: SMTP TLS negotiation failed"


@pytest.mark.asyncio
async def test_allowlist_reject_creates_blocked_log(session, monkeypatch):
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MODE", "dry_run")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ALLOWLIST", "approved@example.com")
    get_settings.cache_clear()

    service = CommercialReportExportService(session)
    schedule = await service.create_schedule(
        {"name": "Allowlist Reject", "frequency": "weekly", "day_of_week": 1, "recipients_json": ["blocked@example.com"]},
        actor="admin@example.com",
    )
    result = await service.run_schedule_now(schedule.id)

    assert result["status"] == "blocked"
    delivery = (await session.execute(select(CommercialReportDeliveryLog))).scalar_one()
    assert delivery.delivery_status == "blocked"
    assert "blocked_by_allowlist" in delivery.error_message


@pytest.mark.asyncio
async def test_max_recipients_reject(session, monkeypatch):
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MODE", "dry_run")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ALLOWLIST", "a@example.com,b@example.com")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MAX_RECIPIENTS", "1")
    get_settings.cache_clear()

    service = CommercialReportExportService(session)
    schedule = await service.create_schedule(
        {
            "name": "Max Recipients",
            "frequency": "weekly",
            "day_of_week": 1,
            "recipients_json": ["a@example.com", "b@example.com"],
        },
        actor="admin@example.com",
    )
    result = await service.run_schedule_now(schedule.id)

    assert result["status"] == "blocked"
    delivery = (await session.execute(select(CommercialReportDeliveryLog))).scalar_one()
    assert "max recipients" in delivery.error_message


@pytest.mark.asyncio
async def test_secret_scanner_blocks_and_logs(session, monkeypatch):
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MODE", "dry_run")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ALLOWLIST", "ops@example.com")
    get_settings.cache_clear()

    service = CommercialReportExportService(session)
    schedule = await service.create_schedule(
        {"name": "Secret Block", "frequency": "weekly", "day_of_week": 1, "recipients_json": ["ops@example.com"]},
        actor="admin@example.com",
    )
    async def fake_report(**kwargs):
        return {"safe": "ok", "leak": "Bearer sk-secret-123456789"}

    monkeypatch.setattr(service, "build_executive_report_data", fake_report)
    result = await service.run_schedule_now(schedule.id)

    assert result["status"] == "blocked"
    delivery = (await session.execute(select(CommercialReportDeliveryLog))).scalar_one()
    assert "blocked_by_security" in delivery.error_message


@pytest.mark.asyncio
async def test_retry_backoff_works(monkeypatch):
    attempts = {"count": 0}
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    def flaky_send():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise __import__("app.services.routing.commercial_report_email", fromlist=["CommercialReportEmailError"]).CommercialReportEmailError(
                "smtp_failure: temporary"
            )
        return {"status": "sent"}

    monkeypatch.setattr("app.services.routing.commercial_report_email.asyncio.sleep", fake_sleep)
    result, retries = await retry_send_with_backoff(flaky_send, retry_count=2, backoff_seconds=3)

    assert result["status"] == "sent"
    assert retries == 1
    assert sleeps == [3]


@pytest.mark.asyncio
async def test_scheduler_uses_smtp_when_opted_in(session, monkeypatch):
    import app.services.routing.commercial_report_email as email_mod

    FakeSMTP.sent_messages = []
    monkeypatch.setattr(email_mod.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MODE", "smtp")
    monkeypatch.setenv("COMMERCIAL_REPORT_SEND_REAL_EMAIL", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_FROM", "reports@example.com")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ALLOWLIST", "ops@example.com")
    get_settings.cache_clear()

    service = CommercialReportExportService(session)
    schedule = await service.create_schedule(
        {"name": "Scheduler SMTP", "frequency": "weekly", "day_of_week": 1, "recipients_json": ["ops@example.com"]},
        actor="admin@example.com",
    )
    schedule.next_run_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await session.commit()

    results = await service.run_due_schedules_once()

    assert results[0]["status"] == "sent"
    assert len(FakeSMTP.sent_messages) == 1


def test_payload_sanitized_for_email_service():
    payload = sanitize_email_payload({"subject": "OK", "items": ["ok", 1]})
    assert payload["subject"] == "OK"
    with pytest.raises(SecurityScanError):
        sanitize_email_payload({"authorization": "Bearer sk-secret-123456789"})


@pytest.mark.asyncio
async def test_delivery_endpoint_and_send_test_require_admin_auth(admin_client):
    send_resp = await admin_client.post("/admin/routing/executive-dashboard/report-schedules/00000000-0000-0000-0000-000000000000/send-test-email")
    list_resp = await admin_client.get("/admin/routing/executive-dashboard/report-deliveries")
    assert send_resp.status_code in (401, 403)
    assert list_resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_delivery_endpoints(admin_client, admin_token_headers, monkeypatch):
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MODE", "dry_run")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ALLOWLIST", "ops@example.com")
    get_settings.cache_clear()

    create_resp = await admin_client.post(
        "/admin/routing/executive-dashboard/report-schedules",
        headers=admin_token_headers,
        json={
            "name": "Endpoint Delivery",
            "frequency": "weekly",
            "day_of_week": 1,
            "recipients_json": ["ops@example.com"],
            "format": "html",
        },
    )
    assert create_resp.status_code == 200
    schedule_id = create_resp.json()["id"]

    test_resp = await admin_client.post(
        f"/admin/routing/executive-dashboard/report-schedules/{schedule_id}/send-test-email",
        headers=admin_token_headers,
    )
    assert test_resp.status_code == 200
    assert test_resp.json()["status"] == "would_send"

    list_resp = await admin_client.get(
        "/admin/routing/executive-dashboard/report-deliveries?status=dry_run&recipient=ops@example.com",
        headers=admin_token_headers,
    )
    assert list_resp.status_code == 200
    payload = list_resp.json()
    assert payload["smtp_mode"] == "dry_run"
    assert payload["allowlist_configured"] is True
    assert payload["counts"]["dry_run"] >= 1
    assert payload["deliveries"][0]["delivery_status"] == "dry_run"
