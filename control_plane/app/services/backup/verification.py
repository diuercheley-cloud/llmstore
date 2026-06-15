import hashlib
from typing import Any

from app.schemas.backup import BackupManifest, BackupVerificationEntry, BackupVerificationResult

from .archive import ArchiveReader
from .crypto import BackupCryptoService


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class BackupVerificationService:
    def __init__(self, crypto: BackupCryptoService):
        self.crypto = crypto

    async def verify(
        self,
        manifest: BackupManifest,
        encrypted_payload: bytes,
    ) -> BackupVerificationResult:
        archive_checksum_valid = _sha256_bytes(encrypted_payload) == manifest.archive_checksum

        signature_valid = self.crypto.verify_signature(
            manifest.payload_signature,
            {
                "backup_id": manifest.backup_id,
                "archive_checksum": manifest.archive_checksum,
                "components": [component.model_dump() for component in manifest.components],
            },
        )

        from app.core.metrics import BACKUP_VERIFICATION_FAILURE_TOTAL

        from .errors import (
            BackupKeyError,
            BackupSignatureError,
            BackupValidationError,
        )

        component_results: list[BackupVerificationEntry] = []
        status = "valid"
        details: dict[str, Any] = {}
        error_code = None

        if not archive_checksum_valid:
            status = "corrupted"
            error_code = BackupValidationError.error_code
            BACKUP_VERIFICATION_FAILURE_TOTAL.labels(reason="checksum_mismatch").inc()

        if not signature_valid:
            status = "corrupted"
            error_code = BackupSignatureError.error_code
            BACKUP_VERIFICATION_FAILURE_TOTAL.labels(reason="signature_invalid").inc()

        if manifest.key_id and manifest.key_id != self.crypto.key_id:
            details["key_id_mismatch"] = (
                f"Expected '{manifest.key_id}', current is '{self.crypto.key_id}'"
            )
            status = "corrupted"
            error_code = BackupKeyError.error_code
            BACKUP_VERIFICATION_FAILURE_TOTAL.labels(reason="key_mismatch").inc()

        try:
            archive_bytes = self.crypto.decrypt(encrypted_payload)
            extracted_parts = ArchiveReader.extract(archive_bytes)

            for component in manifest.components:
                actual_content = extracted_parts.get(component.file_name)
                actual_hash = None
                if actual_content is not None:
                    if isinstance(actual_content, dict):
                        # Re-serialize to get hash if it was a JSON component
                        import json

                        actual_hash = _sha256_bytes(
                            json.dumps(actual_content, sort_keys=True).encode("utf-8")
                        )
                    else:
                        actual_hash = _sha256_bytes(actual_content)

                component_status = "ok" if actual_hash == component.data_hash else "mismatch"
                if component_status != "ok":
                    status = "corrupted"
                    error_code = error_code or BackupValidationError.error_code
                    BACKUP_VERIFICATION_FAILURE_TOTAL.labels(
                        reason=f"component_mismatch:{component.name}"
                    ).inc()

                component_results.append(
                    BackupVerificationEntry(
                        name=component.name,
                        status=component_status,
                        expected_hash=component.data_hash,
                        actual_hash=actual_hash,
                    )
                )
        except Exception as exc:
            status = "corrupted"
            error_code = error_code or BackupValidationError.error_code
            details["error"] = str(exc)
            BACKUP_VERIFICATION_FAILURE_TOTAL.labels(reason="decryption_error").inc()

        return BackupVerificationResult(
            backup_id=manifest.backup_id,
            status=status,
            signature_valid=signature_valid,
            archive_checksum_valid=archive_checksum_valid,
            component_verification=component_results,
            details=details,
            error_code=error_code,
        )
