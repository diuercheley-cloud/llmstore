import hashlib
import logging
import os
import uuid

from app.core.config import get_settings
from app.models.multimodal import MultimodalAsset
from app.services.multimodal.multimodal_policy import MultimodalPolicyService
from app.services.multimodal.multimodal_usage import MultimodalUsageService
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SpeechToTextService:
    @property
    def settings(self):
        return get_settings()

    def __init__(self):
        self.policy_service = MultimodalPolicyService()
        self.usage_service = MultimodalUsageService()
        
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        self.storage_dir = os.path.join(base_dir, "data", "multimodal_assets")
        os.makedirs(self.storage_dir, exist_ok=True)

    async def transcribe_audio(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        audio_file: UploadFile = None,
        base64_audio: str = None,
        save_audio_by_policy: bool = False  # False by default (do not save raw audio)
    ) -> dict:
        # 1. Policy check
        await self.policy_service.check_policy(db, client_id, "speech-to-text")

        audio_bytes = b""
        filename = "audio.wav"
        mime_type = "audio/wav"

        # 2. Extract audio bytes
        if audio_file:
            audio_bytes = await audio_file.read()
            filename = audio_file.filename or "audio.wav"
            mime_type = audio_file.content_type or "audio/wav"
        elif base64_audio:
            import base64
            audio_bytes = base64.b64decode(base64_audio)
        else:
            raise HTTPException(
                status_code=400,
                detail="No audio input provided. Specify upload or base64_audio."
            )

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio bytes provided.")

        # 3. Process transcription using real provider
        from app.services.multimodal.providers.local_whisper import LocalWhisperProvider
        provider = LocalWhisperProvider()
        result = provider.transcribe(audio_bytes)
        
        # Real duration calculation would check audio headers. Here we estimate 1 second per 16KB of audio
        duration_seconds = max(1, int(len(audio_bytes) / 16000))
        detected_language = result.get("language", "en")
        confidence = result.get("confidence", 0.95)
        transcription_text = result.get("text", "")

        # 4. Save raw audio only if save_audio_by_policy is explicitly enabled
        asset_id = None
        if save_audio_by_policy:
            asset_id = uuid.uuid4()
            file_hash = hashlib.sha256(audio_bytes).hexdigest()
            ext = os.path.splitext(filename)[1] or ".wav"
            storage_path = os.path.join(self.storage_dir, f"{asset_id}{ext}")
            
            with open(storage_path, "wb") as f:
                f.write(audio_bytes)

            asset = MultimodalAsset(
                id=asset_id,
                client_id=client_id,
                asset_type="audio",
                storage_path=storage_path,
                file_size_bytes=len(audio_bytes),
                mime_type=mime_type,
                file_hash=file_hash,
                provenance="uploaded",
                exif_sanitized=False,
                metadata_json={"duration_seconds": duration_seconds}
            )
            db.add(asset)
            await db.commit()
            logger.info(f"Raw audio saved as asset: {asset_id}")
        else:
            logger.info("Raw audio was NOT saved to storage as per policy restrictions.")

        # 5. Log request and usage
        req = await self.usage_service.log_request(
            db, client_id, "speech-to-text", "completed", input_asset_id=asset_id
        )
        # Log usage based on duration_seconds
        await self.usage_service.record_usage(
            db, client_id, req.id, "speech-to-text", unit_count=duration_seconds
        )

        return {
            "asset_id": str(asset_id) if asset_id else None,
            "text": transcription_text,
            "duration": duration_seconds,
            "language": detected_language,
            "confidence": confidence
        }
