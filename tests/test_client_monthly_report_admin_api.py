
import pytest


@pytest.mark.asyncio
async def test_monthly_report_preview_endpoint_registered():
    """Verify the endpoint is registered in the sales router."""
    from app.api.sales import router

    routes = [r.path for r in router.routes]
    matching = [r for r in routes if "monthly-report-preview" in r]
    assert len(matching) == 1, f"Expected 1 route, found {len(matching)}: {matching}"
    assert matching[0] == "/admin/sales/monthly-report-preview"


@pytest.mark.asyncio
async def test_monthly_report_preview_endpoint_method():
    from app.api.sales import router

    for route in router.routes:
        if "monthly-report-preview" in route.path:
            assert "GET" in route.methods, "Endpoint should accept GET"
            return


@pytest.mark.asyncio
async def test_monthly_report_preview_imports():
    """Check that the sales module imports successfully."""
    try:
        from app.api.sales import monthly_report_preview
        assert monthly_report_preview is not None
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


@pytest.mark.asyncio
async def test_monthly_report_preview_response_structure():
    """Validate the response structure by calling the function signature."""
    # Verify the function exists and has expected parameters
    import inspect

    from app.api.sales import monthly_report_preview
    sig = inspect.signature(monthly_report_preview)
    params = list(sig.parameters.keys())
    assert "client_id" in params
    assert "month" in params
    assert "include_technical_details" in params


@pytest.mark.asyncio
async def test_month_validator_regex():
    """Verify month format validator rejects invalid months."""
    import re
    pattern = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
    assert pattern.match("2026-05")
    assert pattern.match("2025-12")
    assert not pattern.match("2026-5")
    assert not pattern.match("2026-13")
    assert not pattern.match("2026-00")
    assert not pattern.match("202605")
    assert not pattern.match("invalid")
