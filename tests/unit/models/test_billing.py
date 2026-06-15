from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.api.admin_billing import _serialize_billing_plan_payload
from app.models.billing.billing_plan import BillingPlan
from app.models.core.client import Client
from app.schemas.admin import BillingPlanCreate
from app.services.billing import (
    build_invoice_record_data,
    derive_client_billing_status,
    month_window,
    normalize_invoice_status,
    previous_month_date,
    resolve_effective_plan,
    should_generate_monthly_invoices,
)


def test_resolve_effective_plan_prefers_billing_plan():
    client = Client(
        name="demo",
        rate_limit_per_minute=100,
        daily_token_quota=1000000,
        weekly_token_quota=5000000,
        monthly_token_quota=10000000,
        max_context_tokens=8192,
        max_output_tokens=4096,
    )
    client.billing_plan = BillingPlan(
        code="basic",
        name="Basic",
        rate_limit_per_minute=10,
        daily_token_quota=50000,
        weekly_token_quota=250000,
        monthly_token_quota=500000,
        max_output_tokens=512,
        allow_streaming=True,
        is_active=True,
    )

    effective = resolve_effective_plan(client)

    assert effective.code == "basic"
    assert effective.rate_limit_per_minute == 10
    assert effective.max_output_tokens == 512
    assert effective.allow_streaming is True


def test_resolve_effective_plan_falls_back_to_legacy_client_limits():
    client = Client(
        name="legacy",
        rate_limit_per_minute=7,
        daily_token_quota=21000,
        weekly_token_quota=105000,
        monthly_token_quota=310000,
        max_context_tokens=2048,
        max_output_tokens=900,
    )

    effective = resolve_effective_plan(client)

    assert effective.code == "legacy"
    assert effective.rate_limit_per_minute == 7
    assert effective.max_output_tokens == 900
    assert effective.allow_streaming is True


def test_month_window_returns_calendar_bounds():
    start, end = month_window(date(2026, 4, 30))
    assert start.isoformat() == "2026-04-01"
    assert end.isoformat() == "2026-04-30"


def test_previous_month_date_returns_previous_competence():
    previous = previous_month_date(date(2026, 5, 1))
    assert previous.isoformat() == "2026-04-30"


def test_should_generate_monthly_invoices_only_on_configured_day():
    assert should_generate_monthly_invoices(date(2026, 5, 1), 1) is True
    assert should_generate_monthly_invoices(date(2026, 5, 2), 1) is False


def test_normalize_invoice_status_promotes_pending_to_overdue():
    overdue_since = datetime(2026, 5, 1, 12, 0, tzinfo=UTC) - timedelta(minutes=1)
    status = normalize_invoice_status("pending", overdue_since)
    assert status == "overdue"


def test_derive_client_billing_status_preserves_suspension():
    assert (
        derive_client_billing_status(has_overdue_invoice=True, should_suspend=True) == "suspended"
    )
    assert (
        derive_client_billing_status(has_overdue_invoice=True, should_suspend=False) == "past_due"
    )
    assert derive_client_billing_status(has_overdue_invoice=False, should_suspend=False) == "active"


def test_build_invoice_record_data_uses_preview_values():
    client = Client(
        id="00000000-0000-0000-0000-000000000001",
        name="billing-client",
        billing_status="active",
        billing_plan_id=None,
        rate_limit_per_minute=10,
        daily_token_quota=1000,
        weekly_token_quota=5000,
        monthly_token_quota=2000,
        max_context_tokens=2048,
        max_output_tokens=512,
    )
    effective_plan = resolve_effective_plan(client)

    payload = build_invoice_record_data(
        client=client,
        effective_plan=effective_plan,
        pricing_rule=None,
        monthly_used_tokens=2500,
        period_reference=date(2026, 4, 30),
        due_in_days=7,
        payment_method="manual_pix",
        payment_instructions="pix local",
    )

    assert payload["overage_tokens"] == 500
    assert payload["total_amount"] == Decimal("0.000000")
    assert payload["payment_method"] == "manual_pix"
    assert payload["period_start"].isoformat() == "2026-04-01"


def test_build_invoice_record_data_can_target_previous_month():
    client = Client(
        id="00000000-0000-0000-0000-000000000002",
        name="billing-client-2",
        billing_status="active",
        billing_plan_id=None,
        rate_limit_per_minute=10,
        daily_token_quota=1000,
        weekly_token_quota=5000,
        monthly_token_quota=2000,
        max_context_tokens=2048,
        max_output_tokens=512,
    )
    payload = build_invoice_record_data(
        client=client,
        effective_plan=resolve_effective_plan(client),
        pricing_rule=None,
        monthly_used_tokens=0,
        period_reference=previous_month_date(date(2026, 5, 1)),
        due_in_days=7,
        payment_method="manual_pix",
        payment_instructions="pix local",
    )
    assert payload["period_start"].isoformat() == "2026-04-01"
    assert payload["period_end"].isoformat() == "2026-04-30"


def test_serialize_billing_plan_payload_removes_allowed_models_when_missing():
    payload = BillingPlanCreate(
        code="qa",
        name="QA",
        description="Validation",
        rate_limit_per_minute=10,
        daily_token_quota=1000,
        weekly_token_quota=5000,
        monthly_token_quota=2000,
        max_output_tokens=256,
        allow_streaming=False,
        is_active=True,
        allowed_models=None,
    )

    plan_data = _serialize_billing_plan_payload(payload)

    assert "allowed_models" not in plan_data
    assert plan_data["allowed_models_json"] is None


def test_serialize_billing_plan_payload_serializes_allowed_models_json():
    payload = BillingPlanCreate(
        code="qa2",
        name="QA 2",
        description="Validation",
        rate_limit_per_minute=10,
        daily_token_quota=1000,
        weekly_token_quota=5000,
        monthly_token_quota=2000,
        max_output_tokens=256,
        allow_streaming=True,
        is_active=True,
        allowed_models=["model-a", "model-b"],
    )

    plan_data = _serialize_billing_plan_payload(payload)

    assert "allowed_models" not in plan_data
    assert plan_data["allowed_models_json"] == '["model-a", "model-b"]'
