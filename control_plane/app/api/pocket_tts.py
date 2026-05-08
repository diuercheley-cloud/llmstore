from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse
from app.core.config import get_settings

router = APIRouter(prefix="/pocket-tts", tags=["pocket-tts"])
settings = get_settings()

# O serviço pocket-tts deve estar acessível via rede interna do Docker
# Se rodar como serviço "pocket-tts" no docker-compose, a URL será esta:
POCKET_TTS_URL = "http://pocket-tts:8000"
ui_file = Path(__file__).resolve().parents[1] / "static" / "pocket-tts" / "index.html"


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
async def pocket_tts_ui():
    return FileResponse(ui_file)


@router.api_route("/{path:path}", methods=["GET", "POST"])
async def proxy_pocket_tts(request: Request, path: str):
    url = f"{POCKET_TTS_URL}/{path}"

    params = dict(request.query_params)
    content = await request.body()
    headers = dict(request.headers)

    if "host" in headers:
        del headers["host"]

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            proxy_resp = await client.request(
                method=request.method,
                url=url,
                params=params,
                content=content,
                headers=headers,
            )

            return Response(
                content=proxy_resp.content,
                status_code=proxy_resp.status_code,
                headers=dict(proxy_resp.headers),
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Pocket-TTS service unreachable: {exc}")
