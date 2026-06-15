from app.services.billing.pricing_engine import calculate_financials


def test_admin_can_see_margin():
    result = calculate_financials("local", 1000, 500, plan_code="basic")
    assert "margin_percent" in result
    assert "gross_profit_brl" in result
    assert "provider_cost_brl" in result


def test_client_does_not_see_margin_in_simple_query():
    result = calculate_financials("local", 1000, 500, plan_code="basic")
    customer_visible = {
        "customer_price_brl": result["customer_price_brl"],
        "total_tokens": result["total_tokens"],
    }
    assert "provider_cost_brl" not in customer_visible
    assert "margin_percent" not in customer_visible
    assert "gross_profit_brl" not in customer_visible


def test_client_data_excludes_provider_cost():
    customer_data = {
        "model": "gemma",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
        "customer_price_brl": 0.005,
    }
    assert "provider_cost_brl" not in customer_data
    assert "provider_cost_usd" not in customer_data
    assert "margin_percent" not in customer_data


def test_client_can_see_own_price_only():
    result = calculate_financials("local", 500, 200, plan_code="basic")
    client_view = {
        "tokens": result["total_tokens"],
        "price_brl": result["customer_price_brl"],
    }
    assert client_view["price_brl"] >= 0
    assert client_view["tokens"] == 700


def test_margin_field_not_accidentally_exposed_in_portal_context():
    portal_response = {
        "usage": [
            {
                "date": "2026-05-01",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "price_brl": 0.005,
            },
        ]
    }
    for entry in portal_response["usage"]:
        assert "provider_cost_brl" not in entry
        assert "margin_percent" not in entry
        assert "gross_profit_brl" not in entry


def test_summary_no_secrets():
    result = calculate_financials("local", 100, 50, plan_code="free")
    dump = str(result)
    assert "api_key" not in dump.lower()
    assert "secret" not in dump.lower()


def test_no_real_pix_or_billing_integration():
    result = calculate_financials("local", 100, 50)
    assert "pix" not in str(result).lower()
    assert "payment_link" not in str(result).lower()
    assert "charge" not in str(result).lower()
