import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.deps import get_inference_proxy
from app.api.admin import router as admin_router
from app.api.sales import router as sales_router
from app.api.admin_tests import router as admin_tests_router
from app.api.client import router as client_router
from app.api.rag import router as rag_router, client_rag_router
from app.api.rag_enterprise import router as rag_enterprise_router, admin_router as admin_rag_router
from app.api.portal import router as portal_router
from app.api.public import router as public_router
from app.api.system import router as system_router
from app.api.pocket_tts import router as pocket_tts_router
from app.api.developer_docs import router as developer_docs_router
from app.api.billing_admin import router as billing_admin_router
from app.api.wallet_admin import router as wallet_admin_router
from app.api.providers import router as providers_router
from app.api.routing_admin import router as routing_admin_router
from app.api.hybrid_admin import router as hybrid_admin_router
from app.api.abuse_admin import router as abuse_admin_router
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


app = FastAPI(
    title=settings.project_name,
    description="""
Stack local e portátil para servir modelos de linguagem com separação explícita entre Control Plane e Data Plane.
Oferece compatibilidade com a API OpenAI, gestão de cotas, faturamento e roteamento com fallback.
""",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "system", "description": "Endpoints de saúde e métricas do sistema."},
        {"name": "public", "description": "Endpoints públicos para onboarding e listagem de planos."},
        {"name": "client", "description": "API compatível com OpenAI para consumo dos modelos."},
        {"name": "portal", "description": "API do portal do cliente para gestão de conta e faturas."},
        {"name": "admin", "description": "API administrativa para gestão de clientes, chaves e infraestrutura."},
    ]
)
app.middleware("http")(request_context_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=bool(settings.cors_origins) and "*" not in settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Token", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
)
app.include_router(public_router)
app.include_router(system_router)
app.include_router(admin_router)
app.include_router(sales_router)
app.include_router(admin_tests_router)
app.include_router(client_router)
app.include_router(rag_router)
app.include_router(client_rag_router)
app.include_router(rag_enterprise_router)
app.include_router(admin_rag_router)
app.include_router(portal_router, prefix="/portal")
app.include_router(portal_router, prefix="/v1") # Alias for /account
app.include_router(developer_docs_router)
app.include_router(billing_admin_router)
app.include_router(wallet_admin_router)
app.include_router(providers_router)
app.include_router(routing_admin_router)
app.include_router(hybrid_admin_router)
app.include_router(abuse_admin_router)
app.include_router(pocket_tts_router)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
