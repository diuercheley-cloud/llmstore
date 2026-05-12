import pytest


@pytest.mark.asyncio
async def test_branding_endpoint_registered():
    from app.api.public import router
    routes = [r.path for r in router.routes]
    matching = [r for r in routes if "branding" in r]
    assert len(matching) >= 1, f"No branding route found in {routes}"
    assert "/public/branding" in matching


@pytest.mark.asyncio
async def test_branding_endpoint_method():
    from app.api.public import router
    for route in router.routes:
        if "branding" in route.path:
            assert "GET" in route.methods
            return


@pytest.mark.asyncio
async def test_branding_response_fields():
    from app.services.branding import get_safe_branding
    b = get_safe_branding()
    required = [
        "product_name", "company_name", "tagline", "support_email",
        "primary_color", "secondary_color", "footer_text",
        "show_powered_by", "capabilities_title",
    ]
    for field in required:
        assert field in b, f"Missing field in branding response: {field}"
    assert isinstance(b["show_powered_by"], bool)


@pytest.mark.asyncio
async def test_branding_default_values():
    from app.services.branding import get_safe_branding
    b = get_safe_branding()
    assert b["product_name"] == "LLM Inference Stack"
    assert b["primary_color"] == "#c84c2f"
    assert b["secondary_color"] == "#0f766e"
    assert b["show_powered_by"] is True


@pytest.mark.asyncio
async def test_branding_response_is_public():
    from app.api.public import router
    for route in router.routes:
        if "branding" in route.path:
            # Should not require auth
            deps = [d.dependency for d in route.dependencies] if hasattr(route, "dependencies") else []
            assert len(deps) == 0, "Branding endpoint should not require auth"
            return


@pytest.mark.asyncio
async def test_branding_colors_valid_format():
    from app.services.branding import get_safe_branding
    import re
    b = get_safe_branding()
    hex_pattern = re.compile(r"^#[0-9a-f]{6}$")
    assert hex_pattern.match(b["primary_color"]), f"Invalid hex: {b['primary_color']}"
    assert hex_pattern.match(b["secondary_color"]), f"Invalid hex: {b['secondary_color']}"
