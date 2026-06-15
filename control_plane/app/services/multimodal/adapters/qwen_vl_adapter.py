from app.services.multimodal.base import (
    MultimodalAdapterBase,
    MultimodalCapability,
    MultimodalInputType,
    MultimodalResult,
)


class QwenVLAdapter(MultimodalAdapterBase):
    @property
    def capabilities(self) -> list[MultimodalCapability]:
        return [
            MultimodalCapability.IMAGE_CAPTIONING,
            MultimodalCapability.VISUAL_QUESTION_ANSWERING,
            MultimodalCapability.OCR,
            MultimodalCapability.OBJECT_DETECTION,
        ]

    @property
    def model_name(self) -> str:
        return "Qwen-VL-Chat"

    async def analyze(
        self, input_type: MultimodalInputType, file_path: str, prompt: str | None = None, **kwargs
    ) -> MultimodalResult:
        return MultimodalResult(
            text=f"[Mock Qwen-VL] Analyzing {file_path}. Prompt: {prompt}",
            detected_objects=[{"label": "cat", "box": [10, 10, 50, 50]}],
            ocr_text="Sample OCR text from Qwen-VL",
            confidence=0.92,
            model_used=self.model_name,
            backend_used="mock_backend",
            audit_metadata={"file": file_path},
        )
