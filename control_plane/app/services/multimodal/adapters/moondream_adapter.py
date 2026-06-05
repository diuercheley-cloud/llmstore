from typing import Any, Dict, List, Optional
from app.services.multimodal.base import (
    MultimodalAdapterBase, 
    MultimodalCapability, 
    MultimodalInputType, 
    MultimodalResult
)


class MoondreamAdapter(MultimodalAdapterBase):
    @property
    def capabilities(self) -> List[MultimodalCapability]:
        return [
            MultimodalCapability.IMAGE_CAPTIONING,
            MultimodalCapability.VISUAL_QUESTION_ANSWERING
        ]

    @property
    def model_name(self) -> str:
        return "moondream2"

    async def analyze(
        self, 
        input_type: MultimodalInputType, 
        file_path: str, 
        prompt: Optional[str] = None,
        **kwargs
    ) -> MultimodalResult:
        return MultimodalResult(
            text=f"[Mock Moondream] Tiny model analysis of {file_path}",
            detected_objects=[],
            confidence=0.88,
            model_used=self.model_name,
            backend_used="mock_local",
            audit_metadata={"file": file_path}
        )
