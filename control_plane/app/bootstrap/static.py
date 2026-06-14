# bootstrap/static.py

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def mount_static_files(app: FastAPI, enable_legacy_static: bool = False) -> None:
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if not static_dir.exists():
        return

    modern_static_paths = [
        "admin-v2",
        "portal",
        "shared",
        "www",
        "hub",
        "harness",
        "monitoring",
        "provider-settings",
        "admin-lab",
    ]

    for path_name in modern_static_paths:
        path = static_dir / path_name
        if path.exists():
            app.mount(f"/static/{path_name}", StaticFiles(directory=path), name=f"static-{path_name}")

    if enable_legacy_static:
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
