from decimal import Decimal

from app.services.billing import EffectivePlan, build_invoice_preview, estimate_request_cost


def test_estimate_request_cost_only_charges_overage_delta():
    cost = estimate_request_cost(
        monthly_tokens_used_before=950,
        request_tokens=200,
        included_monthly_tokens=1000,
        overage_price_per_1k_tokens=Decimal("0.050000"),
    )
    assert cost == Decimal("0.007500")


def test_build_invoice_preview_computes_totals():
    preview = build_invoice_preview(
        effective_plan=EffectivePlan(
            code="basic",
            name="Basic",
            rate_limit_per_minute=10,
            daily_token_quota=10000,
            weekly_token_quota=50000,
            monthly_token_quota=1000,
            max_output_tokens=512,
            allow_streaming=True,
            monthly_price=Decimal("19.9000"),
            overage_price_per_1k_tokens=Decimal("0.050000"),
            currency="USD",
        ),
        monthly_used_tokens=2500,
    )
    assert preview["included_tokens"] == 1000
    assert preview["overage_tokens"] == 1500
    assert preview["overage_cost"] == 0.075
    assert preview["total_estimated"] == 19.975
