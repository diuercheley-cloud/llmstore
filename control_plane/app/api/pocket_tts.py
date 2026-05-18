from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.client import Client
from app.services.auth import require_client
from app.services.tts_usage import ensure_tts_quota, record_tts_event, check_tts_feature_blocked
from app.services.billing import resolve_effective_plan

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
async def proxy_pocket_tts(
    request: Request, 
    path: str,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    # Check if TTS is blocked for this client
    is_blocked, block_reason = await check_tts_feature_blocked(session, client.id)
    if is_blocked:
        raise HTTPException(status_code=403, detail=f"TTS feature blocked: {block_reason}")

    effective_plan = resolve_effective_plan(client)
    if not effective_plan.tts_enabled:
        raise HTTPException(status_code=403, detail="TTS feature is not enabled for your plan")

    url = f"{POCKET_TTS_URL}/{path}"
    
    request_content = None
    request_files = None

    # Check quota for /tts endpoint
    chars_to_record = 0
    content_type = request.headers.get("content-type", "")
    is_form_request = request.method == "POST" and (
        "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type
    )
    if is_form_request:
        form_data = await request.form()
        if path == "tts":
            text = form_data.get("text", "")
            if isinstance(text, str):
                chars_to_record = len(text)
                await ensure_tts_quota(session, client, chars_to_record)

        # The form stream is consumed by request.form(); rebuild it for proxying.
        request_files = []
        for key, value in form_data.multi_items():
            if isinstance(value, UploadFile):
                request_files.append((key, (value.filename, await value.read(), value.content_type)))
            else:
                request_files.append((key, (None, str(value))))
    else:
        request_content = await request.body()

    params = dict(request.query_params)
    headers = dict(request.headers)

    if "host" in headers:
        del headers["host"]
    headers.pop("content-length", None)
    if request_files is not None:
        headers.pop("content-type", None)

    # Add X-Client-ID header for internal tracking if needed by pocket-tts
    headers["X-Client-ID"] = str(client.id)

    async with httpx.AsyncClient(timeout=300.0) as httpx_client:
        try:
            proxy_resp = await httpx_client.request(
                method=request.method,
                url=url,
                params=params,
                content=request_content,
                files=request_files,
                headers=headers,
            )

            response = Response(
                content=proxy_resp.content,
                status_code=proxy_resp.status_code,
                headers=dict(proxy_resp.headers),
            )
            
            # Record usage if successful
            if path == "tts" and request.method == "POST" and proxy_resp.status_code in {200, 201}:
                plan = resolve_effective_plan(client)
                await record_tts_event(
                    session,
                    client_id=client.id,
                    chars=chars_to_record,
                    api_key_prefix=request.state.api_key_prefix if hasattr(request.state, "api_key_prefix") else None,
                    audio_size_bytes=len(proxy_resp.content),
                    plan_code=plan.code
                )
                await session.commit()
            
            return response
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Pocket-TTS service unreachable: {exc}")
