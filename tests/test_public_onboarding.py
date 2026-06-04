import pytest
from app.models.billing_plan import BillingPlan
from app.models.pricing_rule import PricingRule
from app.services.public_onboarding import build_account_name, marketing_summary, normalize_email


def test_build_account_name_is_deterministic_and_slugged():
    account_name = build_account_name("Acme AI", "Founders@Acme.ai")
    assert account_name.startswith("founders-")
    assert len(account_name.split("-")[-1]) == 8


def test_normalize_email_rejects_invalid_values():
    with pytest.raises(Exception) as exc_info:
        normalize_email("invalid-email")
    assert getattr(exc_info.value, "status_code", None) == 422


def test_marketing_summary_exposes_customer_facing_plan_fields():
    plan = BillingPlan(
        code="pro",
        name="Pro",
        description="Growth plan",
        rate_limit_per_minute=45,
        daily_token_quota=300000,
        monthly_token_quota=4000000,
        max_output_tokens=1536,
        allow_streaming=True,
        is_active=True,
    )
    plan.pricing_rules = [
        PricingRule(
            currency="USD",
            monthly_price=99,
            overage_price_per_1k_tokens=0.03,
            description="Growth plan",
            is_active=True,
        )
    ]

    summary = marketing_summary(plan, plan.pricing_rules[0])

    assert summary["code"] == "pro"
    assert summary["monthly_price"] == 99.0
    assert summary["allow_streaming"] is True
    assert summary["highlight"] is True
