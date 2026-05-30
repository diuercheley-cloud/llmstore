# Vision Understanding Service

The vision service enables models and agents to process and analyze images safely. It handles image upload, base64 data encoding, and internal URL retrieval, performing automated metadata sanitization and audit logging.

## Endpoint

`POST /v1/multimodal/vision`

### Request parameters (Multipart/Form or URL Encoded)

* `image_file` (file, optional): Uploaded image file.
* `base64_data` (string, optional): Base64-encoded image string.
* `image_url` (string, optional): Secure internal URL to download the image from.
* `run_ocr` (boolean, optional, default: false): Instructs the system to perform OCR on the image.

### Authentication

Clients must authenticate using their bearer token in the `Authorization` header.

## Security Policies

1. **Secure Internal URL Routing**: By default, retrieval of images from external domains is prohibited to prevent SSRF (Server-Side Request Forgery). Only local domains (e.g., `.local`, `.internal`, `localhost`) and private IP ranges (e.g., `10.x.x.x`, `192.168.x.x`) are allowed.
2. **Metadata Sanitization**: All images processed through the system undergo automatic EXIF metadata stripping (using PIL/Pillow) before storage to prevent leakage of private metadata (e.g., GPS coordinates, camera details).
3. **Tenant Isolation**: Processed assets are stored and logged with a reference to the tenant (`client_id`). Access to `/v1/multimodal/assets/{asset_id}` is strictly restricted to the tenant who uploaded/generated the asset.

## Usage Example

### Python

```python
import httpx

headers = {"Authorization": "Bearer sk-your-api-key-here.val"}
files = {"image_file": open("test.jpg", "rb")}

response = httpx.post("http://localhost:8000/v1/multimodal/vision", headers=headers, files=files)
print(response.json())
```

### Curl

```bash
curl -X POST http://localhost:8000/v1/multimodal/vision \
  -H "Authorization: Bearer sk-your-api-key-here.val" \
  -F "base64_data=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
```
