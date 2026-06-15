from app.api.agent_runtime_admin import router as runtime_router
from app.api.agent_tools_admin import router as tools_router
from app.api.agent_workflows_admin import router as workflows_router
from app.services.auth import require_admin
from fastapi.routing import APIRoute


def test_sensitive_agent_admin_routers_require_admin():
    for router in (tools_router, runtime_router, workflows_router):
        routes = [route for route in router.routes if isinstance(route, APIRoute)]
        assert routes
        for route in routes:
            dependencies = [dependency.call for dependency in route.dependant.dependencies]
            assert require_admin in dependencies, (
                f"{route.path} does not require admin authentication"
            )
