import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.core.model_provenance import ModelProvenanceRecord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ModelProvenanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_model(
        self,
        model_id: str,
        source: str,
        license: Optional[str] = None,
        weights_hash: Optional[str] = None,
        tokenizer_hash: Optional[str] = None,
        config_hash: Optional[str] = None,
    ) -> ModelProvenanceRecord:
        record = ModelProvenanceRecord(
            model_id=model_id,
            source=source,
            license=license,
            weights_hash=weights_hash,
            tokenizer_hash=tokenizer_hash,
            config_hash=config_hash,
            signature_status="unverified"
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def verify_provenance(self, record_id: str) -> ModelProvenanceRecord:
        import uuid
        stmt = select(ModelProvenanceRecord).where(ModelProvenanceRecord.id == uuid.UUID(record_id))
        res = await self.db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            raise ValueError("Provenance record not found")

        # Mock verification logic
        # In real life, we would check files on disk or remote checksums
        if record.weights_hash and len(record.weights_hash) == 64:
            record.signature_status = "verified"
        else:
            record.signature_status = "failed"

        record.verified_at = datetime.now()
        await self.db.commit()
        return record


class OutputWatermarker(ABC):
    @abstractmethod
    async def apply_watermark(self, text: str, model_id: str, run_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def verify_watermark(self, text: str) -> Dict[str, Any]:
        pass


class StandardOutputWatermarker(OutputWatermarker):
    """
    Initial implementation of watermarking.
    Supports metadata-based watermarking and placeholder for invisible steganography.
    """
    async def apply_watermark(self, text: str, model_id: str, run_id: str) -> Dict[str, Any]:
        # 1. Generate unique watermark ID
        watermark_id = f"wm-{hashlib.sha256(f'{run_id}{model_id}'.encode()).hexdigest()[:12]}"
        
        # 2. Deterministic verification hash
        verification_hash = hashlib.sha256(f"{text}{watermark_id}".encode()).hexdigest()

        # In a real implementation, we would inject invisible characters or 
        # modify token probabilities here if feature flag is ON.
        
        return {
            "watermark_id": watermark_id,
            "run_id": run_id,
            "model_id": model_id,
            "verification_hash": verification_hash,
            "method": "metadata_audit",
            "applied_at": datetime.now().isoformat()
        }

    async def verify_watermark(self, text: str) -> Dict[str, Any]:
        # Heuristic detection for demo purposes
        # In real life, this would look for statistical anomalies or hidden markers
        return {
            "is_authentic": False, # Placeholder
            "confidence": 0.0,
            "metadata": {}
        }
