from app.services.multimodal.base import (
    MultimodalAdapterBase,
    MultimodalCapability,
    MultimodalInputType,
    MultimodalResult,
)


class Florence2Adapter(MultimodalAdapterBase):
    @property
    def capabilities(self) -> list[MultimodalCapability]:
        return [
            MultimodalCapability.IMAGE_CAPTIONING,
            MultimodalCapability.OCR,
            MultimodalCapability.OBJECT_DETECTION,
        ]

    @property
    def model_name(self) -> str:
        return "florence-2-large"

    async def analyze(
        self, input_type: MultimodalInputType, file_path: str, prompt: str | None = None, **kwargs
    ) -> MultimodalResult:
        return MultimodalResult(
            text=f"[Mock Florence2] Comprehensive analysis of {file_path}",
            detected_objects=[{"label": "person", "box": [100, 100, 400, 400]}],
            ocr_text="Structured OCR from Florence-2",
            confidence=0.97,
            model_used=self.model_name,
            backend_used="mock_hf",
            audit_metadata={"file": file_path},
        )
