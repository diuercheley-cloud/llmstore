from __future__ import annotations

from app.core.request_context import get_correlation_id
from app.schemas.backup import BackupErrorDetail, BackupErrorResponse
from app.services.backup.errors import (
    BackupCryptoError,
    BackupError,
    BackupKeyError,
    BackupManifestError,
    BackupSignatureError,
    BackupValidationError,
    RestoreLockError,
    RestorePromotionError,
    RestoreRollbackError,
    RestoreStagingError,
)
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


def _backup_status_code(exc: BackupError) -> int:
    if isinstance(exc, RestoreLockError):
        return 423
    if isinstance(exc, (BackupManifestError, BackupSignatureError, BackupValidationError)):
        return 400
    if isinstance(exc, BackupKeyError):
        return 500
    if isinstance(
        exc, (RestoreStagingError, RestorePromotionError, RestoreRollbackError, BackupCryptoError)
    ):
        return 500
    return 500


def _backup_error_response(request: Request, exc: BackupError, status_code: int) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "") or get_correlation_id() or ""
    payload = BackupErrorResponse(
        error=BackupErrorDetail(
            code=exc.error_code,
            message=str(exc),
            details=getattr(exc, "details", {}) or {},
        ),
        correlation_id=correlation_id or None,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


async def handle_backup_error(request: Request, exc: BackupError) -> JSONResponse:
    return _backup_error_response(request, exc, _backup_status_code(exc))


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc, BackupError):
        return _backup_error_response(request, exc, _backup_status_code(exc))
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def register_exception_handlers(app) -> None:
    app.add_exception_handler(BackupError, handle_backup_error)
    app.add_exception_handler(HTTPException, handle_http_exception)
