from app.bootstrap.routers import _secure_include_router
from app.services.auth import require_admin
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute


def _dependency_calls(route: APIRoute):
    return [dependency.call for dependency in route.dependant.dependencies]


def test_admin_only_router_receives_central_auth_guard():
    app = FastAPI()
    app.include_router = _secure_include_router(app)
    router = APIRouter(prefix="/admin/example")

    @router.get("/status")
    async def status():
        return {}

    app.include_router(router)
    route = next(route for route in app.routes if isinstance(route, APIRoute))
    assert require_admin in _dependency_calls(route)


def test_mixed_router_is_not_globally_guarded():
    app = FastAPI()
    app.include_router = _secure_include_router(app)
    router = APIRouter()

    @router.get("/health")
    async def health():
        return {}

    @router.get("/admin/status")
    async def admin_status():
        return {}

    app.include_router(router)
    routes = [route for route in app.routes if isinstance(route, APIRoute)]
    assert all(require_admin not in _dependency_calls(route) for route in routes)
