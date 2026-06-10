from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware import deprecation_middleware, request_context_middleware

def configure_middleware(app: FastAPI, settings) -> None:
    app.middleware("http")(request_context_middleware)
    app.middleware("http")(deprecation_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=bool(settings.cors_origins) and "*" not in settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Admin-Token", "X-Correlation-ID"],
        expose_headers=["X-Correlation-ID"],
    )
