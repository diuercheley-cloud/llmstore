from app.bootstrap.exceptions import register_exception_handlers
from app.bootstrap.lifecycle import lifespan
from app.bootstrap.middleware import configure_middleware
from app.bootstrap.routers import register_routers
from app.bootstrap.static import mount_static_files
from app.core.config import get_settings
from fastapi import FastAPI


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.project_name,
        description="""
Stack local e portátil para servir modelos de linguagem com separação explícita entre Control Plane e Data Plane.
Oferece compatibilidade com a API OpenAI, gestão de cotas, faturamento e roteamento com fallback.
""",
        version="1.0.0",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/api-docs",
        redoc_url="/api-redoc",
    )
    register_exception_handlers(app)

    configure_middleware(app, settings)
    mount_static_files(app, settings.enable_legacy_static)
    register_routers(app, settings)

    return app
