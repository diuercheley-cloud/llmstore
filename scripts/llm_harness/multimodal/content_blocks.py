from typing import Any, Literal

from pydantic import BaseModel


class ContentBlock(BaseModel):
    type: str


class TextBlock(ContentBlock):
    type: Literal["text"] = "text"
    text: str


class ImageBlock(ContentBlock):
    type: Literal["image_url"] = "image_url"
    image_url: dict[str, str]  # e.g., {"url": "data:image/png;base64,..."}
    file_path: str | None = None
    metadata: dict[str, Any] | None = None


class AudioBlock(ContentBlock):
    type: Literal["audio_url"] = "audio_url"
    audio_url: dict[str, str]  # e.g., {"url": "data:audio/mpeg;base64,..."}
    file_path: str | None = None
    metadata: dict[str, Any] = {}


class VideoBlock(ContentBlock):
    type: Literal["video_url"] = "video_url"
    video_url: dict[str, str]  # e.g., {"url": "data:video/mp4;base64,..."}
    file_path: str | None = None
    metadata: dict[str, Any] = {}
