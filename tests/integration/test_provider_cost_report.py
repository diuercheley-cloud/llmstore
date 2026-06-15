import json
import shutil
from pathlib import Path

import pytest


@pytest.fixture
def mock_validation_data():
    base_dir = Path("artifacts/real-provider-validation/costs")
    run_dir = base_dir / "20991231235959"
    run_dir.mkdir(parents=True, exist_ok=True)

    report_file = run_dir / "provider-costs.json"
    test_data = [
        {
            "provider": "openai",
            "model": "test-model",
            "endpoint_type": "chat",
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "latency_ms": 150,
            "provider_cost_usd": 0.0001,
            "provider_cost_brl": 0.0005,
            "customer_price_brl": 0.001,
            "gross_profit_brl": 0.0005,
            "margin_percent": 50.0,
            "pricing_source": "config",
            "status": "PASS",
        }
    ]
    with open(report_file, "w") as f:
        json.dump(test_data, f)

    yield test_data

    shutil.rmtree(run_dir)


@pytest.mark.asyncio
async def test_get_latest_provider_cost_validation(
    mock_validation_data, admin_client, admin_token_headers
):
    response = await admin_client.get(
        "/admin/providers/cost-validation/latest", headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "run" in data
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["provider"] == "openai"


@pytest.mark.asyncio
async def test_get_latest_provider_cost_validation_no_data(admin_client, admin_token_headers):
    base_dir = Path("artifacts/real-provider-validation/costs")
    if base_dir.exists():
        shutil.rmtree(base_dir)

    response = await admin_client.get(
        "/admin/providers/cost-validation/latest", headers=admin_token_headers
    )
    assert response.status_code == 404
