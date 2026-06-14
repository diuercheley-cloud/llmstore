from fastapi.routing import APIRoute

from app.bootstrap.app_factory import create_app


def test_supported_routes_have_minimal_surface_coverage():
    app = create_app()
    route_index = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }

    expected_routes = {
        ("GET", "/pocket-tts/{path:path}"),
        ("POST", "/pocket-tts/{path:path}"),
        ("GET", "/sitemap.xml"),
        ("GET", "/robots.txt"),
        ("GET", "/{page}.html"),
    }

    missing = sorted(expected_routes - route_index)
    assert not missing, missing
