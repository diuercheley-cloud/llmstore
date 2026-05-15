import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import get_settings
from app.models.commercial_routing_event import CommercialRoutingEvent
from app.services.routing.commercial_report_export import (
    CommercialReportExportService,
    export_executive_report_csv,
    export_executive_report_html,
    export_executive_report_pdf_optional,
    sanitize_report_payload,
)


@pytest.mark.asyncio
async def test_export_json_csv_html(session):
    now = datetime.now(timezone.utc)
    session.add(
        CommercialRoutingEvent(
            client_id=uuid.uuid4(),
            selected_provider="provider-a",
            selected_model="model-x",
            actual_revenue_brl=10.0,
            actual_cost_brl=4.0,
            actual_margin_brl=6.0,
            actual_margin_percent=60.0,
            estimated_revenue_brl=10.0,
            estimated_cost_brl=5.0,
            latency_ms=180,
            created_at=now - timedelta(hours=1),
        )
    )
    await session.commit()

    service = CommercialReportExportService(session)
    report = await service.build_executive_report_data(hours=24)

    assert report["profitability"]["actual_revenue_brl"] == 10.0

    csv_content = export_executive_report_csv(report)
    html_content = export_executive_report_html(report)

    assert "actual_revenue_brl" in csv_content
    assert "Commercial Executive Report" in html_content
    assert report["security_observations"]["scanner_status"] == "passed"


@pytest.mark.asyncio
async def test_filters_function(session):
    now = datetime.now(timezone.utc)
    target_client = uuid.uuid4()
    session.add_all(
        [
            CommercialRoutingEvent(
                client_id=target_client,
                selected_provider="provider-a",
                selected_model="model-x",
                actual_revenue_brl=8.0,
                actual_cost_brl=2.0,
                actual_margin_brl=6.0,
                actual_margin_percent=75.0,
                estimated_revenue_brl=8.0,
                estimated_cost_brl=2.5,
                latency_ms=100,
                created_at=now - timedelta(hours=1),
            ),
            CommercialRoutingEvent(
                client_id=uuid.uuid4(),
                selected_provider="provider-b",
                selected_model="model-y",
                actual_revenue_brl=4.0,
                actual_cost_brl=3.0,
                actual_margin_brl=1.0,
                actual_margin_percent=25.0,
                estimated_revenue_brl=4.0,
                estimated_cost_brl=3.0,
                latency_ms=250,
                created_at=now - timedelta(hours=1),
            ),
        ]
    )
    await session.commit()

    service = CommercialReportExportService(session)
    report = await service.build_executive_report_data(hours=24, client_id=target_client, provider="provider-a", model="model-x")

    assert report["profitability"]["actual_revenue_brl"] == 8.0
    assert len(report["top_clients_profitable"]) == 1
    assert report["top_clients_profitable"][0]["client_id"] == str(target_client)


def test_payload_sanitized():
    payload = sanitize_report_payload(
        {
            "api_key": "TEST_API_KEY",
            "nested": {"authorization": "Bearer bearer-test-token"},
            "prompt": "full prompt",
            "safe": "ok",
        }
    )
    assert payload["api_key"] == "[REDACTED]"
    assert payload["nested"]["authorization"] == "[REDACTED]"
    assert payload["prompt"] == "[REDACTED]"
    assert payload["safe"] == "ok"


def test_scanner_blocks_fake_secret():
    with pytest.raises(Exception) as exc:
        sanitize_report_payload({"safe": "Authorization: Bearer bearer-test-token"})
    assert "Export blocked by security scanner" in str(exc.value)


def test_pdf_unsupported_returns_501(monkeypatch):
    import app.services.routing.commercial_report_export as mod

    monkeypatch.setattr(mod.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(Exception) as exc:
        export_executive_report_pdf_optional({"generated_at_utc": "2026-05-14T00:00:00+00:00"})
    assert getattr(exc.value, "status_code", None) == 501


@pytest.mark.asyncio
async def test_schedule_create_list_disable_enable_and_run_disabled(session, monkeypatch):
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ENABLED", "false")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MODE", "disabled")
    get_settings.cache_clear()

    service = CommercialReportExportService(session)
    schedule = await service.create_schedule(
        {
            "name": "Monthly Export",
            "frequency": "monthly",
            "day_of_month": 1,
            "hour_utc": 8,
            "format": "html",
            "recipients_json": ["ops@example.com"],
            "filters_json": {"hours": 24},
        },
        actor="admin@example.com",
    )
    assert schedule.next_run_at is not None

    listed = await service.list_schedules()
    assert len(listed) == 1
    assert listed[0].name == "Monthly Export"

    disabled = await service.set_schedule_enabled(schedule.id, False)
    assert disabled.enabled is False
    assert disabled.next_run_at is None

    enabled = await service.set_schedule_enabled(schedule.id, True)
    assert enabled.enabled is True
    assert enabled.next_run_at is not None

    result = await service.run_schedule_now(schedule.id)
    assert result["status"] == "email_disabled"
    assert result["report"] is not None
    assert "preview_html" in result


@pytest.mark.asyncio
async def test_run_now_dry_run(session, monkeypatch):
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MODE", "dry_run")
    monkeypatch.setenv("COMMERCIAL_REPORT_SEND_REAL_EMAIL", "false")
    get_settings.cache_clear()

    service = CommercialReportExportService(session)
    schedule = await service.create_schedule(
        {
            "name": "Weekly Export",
            "frequency": "weekly",
            "day_of_week": 1,
            "hour_utc": 8,
            "format": "json",
            "recipients_json": ["finops@example.com"],
            "filters_json": {"hours": 24},
        },
        actor="admin@example.com",
    )
    result = await service.run_schedule_now(schedule.id)
    assert result["status"] == "would_send"
    assert result["report"] is None


@pytest.mark.asyncio
async def test_admin_endpoints_require_auth(admin_client):
    export_resp = await admin_client.get("/admin/routing/executive-dashboard/export?format=json")
    preview_resp = await admin_client.get("/admin/routing/executive-dashboard/export/preview")
    schedule_resp = await admin_client.get("/admin/routing/executive-dashboard/report-schedules")

    assert export_resp.status_code in (401, 403)
    assert preview_resp.status_code in (401, 403)
    assert schedule_resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_endpoints_export_and_schedule(admin_client, admin_token_headers, monkeypatch):
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ENABLED", "false")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_MODE", "disabled")
    get_settings.cache_clear()

    create_resp = await admin_client.post(
        "/admin/routing/executive-dashboard/report-schedules",
        headers=admin_token_headers,
        json={
            "name": "Monthly Export",
            "frequency": "monthly",
            "day_of_month": 1,
            "hour_utc": 8,
            "format": "html",
            "recipients_json": ["ops@example.com"],
            "filters_json": {"hours": 24},
        },
    )
    assert create_resp.status_code == 200
    schedule_id = create_resp.json()["id"]

    list_resp = await admin_client.get("/admin/routing/executive-dashboard/report-schedules", headers=admin_token_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    export_resp = await admin_client.get(
        "/admin/routing/executive-dashboard/export?format=json&hours=24",
        headers=admin_token_headers,
    )
    assert export_resp.status_code == 200
    assert export_resp.json()["security_observations"]["scanner_status"] == "passed"

    csv_resp = await admin_client.get(
        "/admin/routing/executive-dashboard/export?format=csv&hours=24",
        headers=admin_token_headers,
    )
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]

    html_resp = await admin_client.get(
        "/admin/routing/executive-dashboard/export?format=html&hours=24",
        headers=admin_token_headers,
    )
    assert html_resp.status_code == 200
    assert "Commercial Executive Report" in html_resp.text

    preview_resp = await admin_client.get(
        "/admin/routing/executive-dashboard/export/preview?hours=24",
        headers=admin_token_headers,
    )
    assert preview_resp.status_code == 200
    assert "Commercial Executive Report" in preview_resp.text

    run_resp = await admin_client.post(
        f"/admin/routing/executive-dashboard/report-schedules/{schedule_id}/run-now",
        headers=admin_token_headers,
    )
    assert run_resp.status_code == 200
    assert run_resp.json()["status"] == "email_disabled"

    disable_resp = await admin_client.post(
        f"/admin/routing/executive-dashboard/report-schedules/{schedule_id}/disable",
        headers=admin_token_headers,
    )
    assert disable_resp.status_code == 200
    assert disable_resp.json()["enabled"] is False

    enable_resp = await admin_client.post(
        f"/admin/routing/executive-dashboard/report-schedules/{schedule_id}/enable",
        headers=admin_token_headers,
    )
    assert enable_resp.status_code == 200
    assert enable_resp.json()["enabled"] is True
