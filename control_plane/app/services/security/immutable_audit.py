import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from app.core.time import utc_now
from app.domains.audit.contracts import AuditEntryData
from app.domains.audit.repositories import SqlAlchemyAuditRepository
from app.models.agents.immutable_audit import ImmutableAuditLog
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ImmutableAuditStore:
    _private_key = None

    @classmethod
    def get_private_key(cls) -> ed25519.Ed25519PrivateKey:
        """Loads or generates the Ed25519 private key for signing logs."""
        if cls._private_key is not None:
            return cls._private_key

        key_path = os.getenv(
            "AUDIT_PRIVATE_KEY_PATH",
            "/home/kleber/llm-inference-stack/control_plane/.local_ed25519_key",
        )
        if os.path.exists(key_path):
            try:
                with open(key_path, "rb") as f:
                    key_data = f.read()
                cls._private_key = serialization.load_pem_private_key(key_data, password=None)
                logger.info(f"Loaded Ed25519 private key from {key_path}")
                return cls._private_key
            except Exception as e:
                logger.warning(f"Failed to load key from {key_path}: {e}. Generating new key.")

        # Fallback: Generate and save
        private_key = ed25519.Ed25519PrivateKey.generate()
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        try:
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            with open(key_path, "wb") as f:
                f.write(pem)
            logger.info(f"Generated new Ed25519 private key at {key_path}")
        except Exception as e:
            logger.error(f"Failed to write private key to {key_path}: {e}")

        cls._private_key = private_key
        return private_key

    @classmethod
    def get_public_key(cls) -> ed25519.Ed25519PublicKey:
        """Gets the public key corresponding to the private key."""
        return cls.get_private_key().public_key()

    @classmethod
    def format_timestamp(cls, dt: datetime) -> str:
        """Standardizes datetime objects to ISO 8601 strings with timezone offset."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dt_utc = dt.astimezone(UTC)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")

    @classmethod
    async def write_entry(
        cls, db: AsyncSession, action: str, actor: str, payload: dict[str, Any], tenant_id: str
    ) -> None:
        """
        Appends a new cryptographically signed entry to the hash chain using the AuditRepository.
        """
        repo = SqlAlchemyAuditRepository(db)

        # We need the hash before signing, but repo computes it during record_event.
        # So we'll manually compute it here to sign, OR we let repo return the hash.

        now = utc_now()
        previous_hash = await repo.get_last_hash()
        payload_str = json.dumps(payload, sort_keys=True)
        timestamp_str = cls.format_timestamp(now)

        # Re-using the logic from repo for consistency or just using a helper
        raw_data = f"{action}|{actor}|{payload_str}|{timestamp_str}|{previous_hash or ''}"
        record_hash = hashlib.sha256(raw_data.encode("utf-8")).hexdigest()

        # Sign
        private_key = cls.get_private_key()
        signature_bytes = private_key.sign(record_hash.encode("utf-8"))
        signature_hex = signature_bytes.hex()

        entry_data = AuditEntryData(
            id="", timestamp=now, action=action, actor=actor, payload=payload, tenant_id=tenant_id
        )

        await repo.record_event(entry_data, signature=signature_hex)
        logger.info(
            f"[IMMUTABLE AUDIT] Logged block | Action: {action} | Hash: {record_hash[:8]}..."
        )

    @classmethod
    async def verify_chain(cls, db: AsyncSession) -> tuple[bool, int | None, str | None]:
        """
        Iterates over the entire hash chain and validates integrity.
        """
        # For simplicity in this migration, we'll keep using direct model for verify_chain
        # as it's a complex multi-record operation.
        stmt = select(ImmutableAuditLog).order_by(ImmutableAuditLog.id.asc())
        res = await db.execute(stmt)
        entries = res.scalars().all()

        public_key = cls.get_public_key()
        expected_prev_hash = None

        for entry in entries:
            if entry.previous_hash != expected_prev_hash:
                return (
                    False,
                    entry.id,
                    f"Chain broken: expected previous hash {expected_prev_hash}, got {entry.previous_hash}",
                )

            raw_data = f"{entry.action}|{entry.actor}|{entry.payload}|{cls.format_timestamp(entry.created_at)}|{entry.previous_hash or ''}"
            recalculated_hash = hashlib.sha256(raw_data.encode("utf-8")).hexdigest()

            if recalculated_hash != entry.hash:
                return (
                    False,
                    entry.id,
                    f"Hash mismatch: recalculated {recalculated_hash}, stored {entry.hash}",
                )

            try:
                sig_bytes = bytes.fromhex(entry.signature)
                public_key.verify(sig_bytes, entry.hash.encode("utf-8"))
            except Exception as e:
                return False, entry.id, f"Invalid signature: {str(e)}"

            expected_prev_hash = entry.hash

        return True, None, None

    @classmethod
    async def export_logs(cls, db: AsyncSession) -> list[dict[str, Any]]:
        repo = SqlAlchemyAuditRepository(db)
        events = await repo.list_events(limit=1000)
        return [e.model_dump() for e in events]
