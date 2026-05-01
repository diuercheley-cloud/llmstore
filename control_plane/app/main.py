import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.deps import get_inference_proxy
from app.api.admin import router as admin_router
from app.api.client import router as client_router
from app.api.portal import router as portal_router
from app.api.public import router as public_router
from app.api.system import router as system_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.runtime_security import validate_runtime_security
from app.db.session import SessionLocal, engine, redis_client
from app.middleware import request_context_middleware
from app.services.billing_scheduler import billing_scheduler_loop
from app.services.seed import seed_defaults

configure_logging()
settings = get_settings()
validate_runtime_security(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with SessionLocal() as session:
        await seed_defaults(session)
        await session.commit()
    stop_event = asyncio.Event()
    scheduler_task = asyncio.create_task(billing_scheduler_loop(stop_event))
    yield
    stop_event.set()
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    await get_inference_proxy().close()
    await redis_client.aclose()
    await engine.dispose()


app = FastAPI(title=settings.project_name, debug=settings.debug, lifespan=lifespan)
app.middleware("http")(request_context_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=bool(settings.cors_origins),
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Token", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
)
app.include_router(system_router)
app.include_router(public_router)
app.include_router(admin_router)
app.include_router(client_router)
app.include_router(portal_router, prefix="/portal")
app.include_router(portal_router, prefix="/v1") # Alias for /account

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
