# bootstrap/static.py

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

def mount_static_files(app: FastAPI):
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
