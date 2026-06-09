"""Small registry helpers used to keep FastAPI bootstrap declarative."""

from collections.abc import Iterable
from typing import Any

from fastapi import FastAPI


def register_routers(app: FastAPI, routers: Iterable[Any]) -> None:
    """Register routers once and fail fast when a duplicate object is supplied."""
    seen: set[int] = set()
    for router in routers:
        identity = id(router)
        if identity in seen:
            raise RuntimeError(f"Duplicate router registration: {router!r}")
        seen.add(identity)
        app.include_router(router)
