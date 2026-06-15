from app.services.multimodal.base import (
    MultimodalAdapterBase,
    MultimodalCapability,
    MultimodalInputType,
    MultimodalResult,
)


class LlavaAdapter(MultimodalAdapterBase):
    @property
    def capabilities(self) -> list[MultimodalCapability]:
        return [
            MultimodalCapability.IMAGE_CAPTIONING,
            MultimodalCapability.VISUAL_QUESTION_ANSWERING,
        ]

    @property
    def model_name(self) -> str:
        return "llava-v1.5-7b"

    async def analyze(
        self, input_type: MultimodalInputType, file_path: str, prompt: str | None = None, **kwargs
    ) -> MultimodalResult:
        # Mock implementation for placeholder
        return MultimodalResult(
            text=f"[Mock Llava] I see an image at {file_path}. Prompt: {prompt}",
            detected_objects=[],
            confidence=0.95,
            model_used=self.model_name,
            backend_used="mock_vllm",
            audit_metadata={"file": file_path},
        )
