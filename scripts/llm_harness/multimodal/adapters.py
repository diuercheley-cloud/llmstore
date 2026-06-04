from typing import Any, Dict, List


def adapt_content_blocks_for_provider(
    blocks: List[Any],
    multimodal_enabled: bool = False
) -> List[Dict[str, Any]]:
    """
    Adapts content blocks (TextBlock, ImageBlock, etc. or dicts) for a provider.
    Fails with ValueError if provider doesn't support multimodal (multimodal_enabled is False)
    but multimodal blocks are present.
    """
    has_media = False
    adapted: List[Dict[str, Any]] = []

    for block in blocks:
        if hasattr(block, "model_dump"):
            b_dict = block.model_dump()
        elif isinstance(block, dict):
            b_dict = block
        else:
            # Fallback for simple strings or other types
            adapted.append({"type": "text", "text": str(block)})
            continue

        b_type = b_dict.get("type")
        if b_type == "image_url":
            has_media = True

        if b_type == "text":
            adapted.append({
                "type": "text",
                "text": b_dict.get("text", "")
            })
        elif b_type == "image_url":
            # Verify no direct raw base64 leaks in raw metadata if possible,
            # but keep standard image_url
            adapted.append({
                "type": "image_url",
                "image_url": b_dict.get("image_url", {})
            })
        elif b_type == "audio_url":
            # AudioBlock is metadata-only - do not embed base64
            url_val = b_dict.get("audio_url", {}).get("url", "")
            if url_val.startswith("data:") and ";base64," in url_val:
                url_val = "data:audio/mpeg;base64,[REDACTED]"
            adapted.append({
                "type": "audio_url",
                "audio_url": {"url": url_val},
                "metadata": b_dict.get("metadata", {})
            })
        elif b_type == "video_url":
            # VideoBlock is metadata-only - do not embed base64
            url_val = b_dict.get("video_url", {}).get("url", "")
            if url_val.startswith("data:") and ";base64," in url_val:
                url_val = "data:video/mp4;base64,[REDACTED]"
            adapted.append({
                "type": "video_url",
                "video_url": {"url": url_val},
                "metadata": b_dict.get("metadata", {})
            })
        else:
            adapted.append(b_dict)

    if has_media and not multimodal_enabled:
        raise ValueError(
            "Provider or model does not support multimodal input. "
            "Enable 'multimodal' or choose a multimodal model."
        )

    return adapted
