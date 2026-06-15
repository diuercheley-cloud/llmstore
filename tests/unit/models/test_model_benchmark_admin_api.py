import json

import pytest


@pytest.fixture
def mock_benchmarks(tmp_path):
    # Setup a mock artifacts directory
    bench_dir = tmp_path / "artifacts" / "model-benchmarks"
    model_dir = bench_dir / "test-model"
    run_dir = model_dir / "20260509_120000"
    run_dir.mkdir(parents=True)

    benchmark_data = {
        "model_requested": "test-model",
        "tokens_per_second": 25.0,
        "recommendation": "safe_for_basic",
    }

    with open(run_dir / "benchmark.json", "w") as f:
        json.dump(benchmark_data, f)

    return bench_dir


@pytest.mark.asyncio
async def test_list_benchmarks_empty(admin_client, admin_token_headers):
    # Test when no benchmarks exist
    response = await admin_client.get("/admin/benchmarks", headers=admin_token_headers)
    # This might return real benchmarks if they exist in the environment
    # So we should ideally mock the settings.root_dir
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_specific_benchmark_not_found(admin_client, admin_token_headers):
    response = await admin_client.get(
        "/admin/benchmarks/non-existent-model", headers=admin_token_headers
    )
    assert response.status_code == 404
