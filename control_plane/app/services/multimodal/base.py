from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class MultimodalInputType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"


class MultimodalCapability(str, Enum):
    IMAGE_CAPTIONING = "image_captioning"
    VISUAL_QUESTION_ANSWERING = "visual_question_answering"
    OCR = "ocr"
    OBJECT_DETECTION = "object_detection"
    VIDEO_SUMMARY = "video_summary"
    FRAME_QUESTION_ANSWERING = "frame_question_answering"


@dataclass
class MultimodalResult:
    text: str
    detected_objects: list[dict[str, Any]]
    ocr_text: str | None = None
    confidence: float = 0.0
    model_used: str = "unknown"
    backend_used: str = "unknown"
    audit_metadata: dict[str, Any] = None


class MultimodalAdapterBase(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> list[MultimodalCapability]:
        """List capabilities supported by this adapter."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The specific model name this adapter handles."""
        pass

    @abstractmethod
    async def analyze(
        self, input_type: MultimodalInputType, file_path: str, prompt: str | None = None, **kwargs
    ) -> MultimodalResult:
        """Perform multimodal analysis."""
        pass

    def supports_capability(self, capability: MultimodalCapability) -> bool:
        return capability in self.capabilities
