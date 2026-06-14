from __future__ import annotations

from fastapi import HTTPException


class BackupError(Exception):
    """Base class for backup/restore errors."""

    error_code = "BACKUP_INTERNAL_ERROR"

    def __init__(self, message: str = "", *, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


class BackupValidationError(BackupError):
    """Raised when backup data validation fails."""
    error_code = "BACKUP_VALIDATION_FAILED"

class BackupCryptoError(BackupError):
    """Raised when encryption or signing fails."""
    error_code = "BACKUP_CRYPTO_ERROR"

class BackupManifestError(BackupError, ValueError):
    """Raised when manifest operations fail."""
    error_code = "BACKUP_MANIFEST_INVALID"

class BackupSignatureError(BackupError):
    """Raised when signature verification fails."""
    error_code = "BACKUP_SIGNATURE_INVALID"

class BackupKeyError(BackupCryptoError, ValueError):
    """Raised when backup encryption key is missing or invalid."""
    error_code = "BACKUP_KEY_MISSING"

class BackupArchiveError(BackupError):
    """Raised when archive creation or extraction fails."""
    error_code = "BACKUP_ARCHIVE_ERROR"

class BackupVerificationError(BackupError):
    """Raised when backup verification fails."""
    error_code = "BACKUP_VERIFICATION_FAILED"


class RestoreLockError(HTTPException, BackupError):
    """Raised when restore lock cannot be acquired."""
    error_code = "RESTORE_LOCKED"

    def __init__(self, message: str = "Restore is already in progress", *, details: dict | None = None):
        HTTPException.__init__(self, status_code=423, detail=message)
        BackupError.__init__(self, message, details=details)

class RestorePlanError(BackupError):
    """Raised when restore planning fails."""
    error_code = "RESTORE_PLAN_FAILED"

class RestoreStagingError(BackupError):
    """Raised when staging environment setup or validation fails."""
    error_code = "RESTORE_STAGING_FAILED"

class RestorePromotionError(BackupError):
    """Raised when promotion to production fails."""
    error_code = "RESTORE_PROMOTION_FAILED"

class RestoreRollbackError(BackupError):
    """Raised when automatic rollback fails."""
    error_code = "RESTORE_ROLLBACK_FAILED"
