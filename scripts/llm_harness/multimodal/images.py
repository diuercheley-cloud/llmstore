import hashlib
import os
from typing import Optional, Tuple

from pydantic import BaseModel

from ..policy import PolicyEngine


class ImageMetadata(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    dimensions: Optional[Tuple[int, int]] = None

def get_image_metadata(abs_path: str) -> ImageMetadata:
    filename = os.path.basename(abs_path)
    ext = os.path.splitext(abs_path)[1].lower().strip(".")
    mime_type = f"image/{ext}"
    if ext == "jpg":
        mime_type = "image/jpeg"
        
    size_bytes = os.path.getsize(abs_path)
    
    sha256_hash = hashlib.sha256()
    with open(abs_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    sha256 = sha256_hash.hexdigest()
    
    dimensions = None
    try:
        from PIL import Image
        with Image.open(abs_path) as img:
            dimensions = img.size
    except ImportError:
        pass
    except Exception:
        pass
        
    return ImageMetadata(
        filename=filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        sha256=sha256,
        dimensions=dimensions
    )

def validate_and_load_image(
    file_path: str,
    workspace_path: str,
    max_size_bytes: int = 10 * 1024 * 1024
) -> Tuple[ImageMetadata, str]:
    """
    Validates the image file, checks policy and workspace constraints,
    and loads its base64 content.
    Returns (metadata, base64_content).
    """
    # Accept: png, jpg, jpeg, webp
    ext = os.path.splitext(file_path)[1].lower().strip(".")
    if ext not in ("png", "jpg", "jpeg", "webp"):
        raise ValueError(f"Unsupported image extension: .{ext}")

    # Validate path within workspace repository
    abs_workspace = os.path.abspath(workspace_path)
    if os.path.isabs(file_path):
        abs_path = os.path.abspath(file_path)
    else:
        abs_path = os.path.abspath(os.path.join(abs_workspace, file_path))

    if not abs_path.startswith(abs_workspace):
        raise PermissionError("Image file path is outside the workspace repository.")

    # Validate with policy
    pe = PolicyEngine()
    rel_path = file_path
    if os.path.isabs(file_path):
        try:
            rel_path = os.path.relpath(file_path, workspace_path)
        except ValueError:
            pass
    dec = pe.evaluate_file_path(rel_path)
    if not dec.allowed:
        raise PermissionError(f"Image path blocked by policy: {dec.reason}")

    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Image not found at path: {file_path}")

    # Validate maximum size
    size_bytes = os.path.getsize(abs_path)
    if size_bytes > max_size_bytes:
        raise ValueError(
            f"Image size {size_bytes} exceeds the maximum limit of "
            f"{max_size_bytes} bytes."
        )

    # Read base64
    import base64
    with open(abs_path, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode("utf-8")

    metadata = get_image_metadata(abs_path)
    
    # Verify that the loaded base64 is not leaked or logged in reports
    # (Sanitizer handles this, but we also ensure no direct storage in logs)
    return metadata, b64_data
