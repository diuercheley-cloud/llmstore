from app.services.multimodal.base import (
    MultimodalAdapterBase,
    MultimodalCapability,
    MultimodalInputType,
    MultimodalResult,
)


class VideoLlamaAdapter(MultimodalAdapterBase):
    @property
    def capabilities(self) -> list[MultimodalCapability]:
        return [MultimodalCapability.VIDEO_SUMMARY, MultimodalCapability.FRAME_QUESTION_ANSWERING]

    @property
    def model_name(self) -> str:
        return "Video-LLaMA"

    async def analyze(
        self, input_type: MultimodalInputType, file_path: str, prompt: str | None = None, **kwargs
    ) -> MultimodalResult:
        return MultimodalResult(
            text=f"[Mock VideoLlama] Video analysis of {file_path}. Prompt: {prompt}",
            detected_objects=[],
            confidence=0.85,
            model_used=self.model_name,
            backend_used="mock_video_backend",
            audit_metadata={"file": file_path, "type": "video"},
        )
