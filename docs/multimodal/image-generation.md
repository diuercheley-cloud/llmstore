# Image Generation Service

The image generation service allows agents and clients to generate visual assets from textual prompts. Access is guarded by tenant quotas, content safety filters, and feature flags.

## Endpoint

`POST /v1/multimodal/image-generation`

### Request Parameters (JSON)

* `prompt` (string, required): The description of the image to generate.
* `size` (string, optional, default: `"1024x1024"`): Target dimensions of the generated image. Supported values: `"256x256"`, `"512x512"`, `"1024x1024"`.
* `provider` (string, optional, default: `"mock"`): The backend provider to use for generation. Supported providers: `"mock"`, `"stable-diffusion"`, `"flux"`, `"openai"`.

### Response Format (JSON)

```json
{
  "asset_id": "a9d59218-472d-426c-8438-fb86de1f32a4",
  "prompt": "A beautiful blue sky",
  "provider": "mock",
  "provenance": "generated_mock",
  "url": "/v1/multimodal/assets/a9d59218-472d-426c-8438-fb86de1f32a4"
}
```

## Security & Governance Policies

1. **Feature Flag Guard**: Access to the endpoint is blocked with a `403 Forbidden` error if `IMAGE_GENERATION_ENABLED=false`.
2. **Content Safety Checks**: Prompts containing forbidden keywords or unsafe concepts are automatically rejected, triggering a `multimodal_policy_events` record.
3. **Budget/Quota Enforcements**: Limits are enforced per client/tenant. When a tenant exceeds their monthly budget (capped at $10.00 in production, or 10 requests per test client during evaluations), requests are blocked with a `429 Too Many Requests`.
4. **Provenance & Audit Trails**: Every generated image is assigned a provenance label matching its provider (e.g., `generated_mock`, `generated_flux`, etc.) and registered in the `multimodal_assets` database table.

## Provider Options

* **Mock Provider (default)**: Generates a lightweight, solid-color PNG corresponding to the dominant color mentioned in the prompt (e.g., green, red, yellow) and stores it with appropriate metadata.
* **Stable Diffusion / Flux / OpenAI**: Integrations can be configured by pointing the service settings to the respective API host and supplying credentials.

## Usage Example

### Python

```python
import httpx

headers = {"Authorization": "Bearer sk-your-api-key-here.val"}
payload = {
    "prompt": "A futuristic city in the style of neon cyberpunk, yellow colors",
    "size": "512x512",
    "provider": "mock"
}

response = httpx.post("http://localhost:8000/v1/multimodal/image-generation", headers=headers, json=payload)
print(response.json())
```

### Curl

```bash
curl -X POST http://localhost:8000/v1/multimodal/image-generation \
  -H "Authorization: Bearer sk-your-api-key-here.val" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A peaceful green meadow", "size": "1024x1024", "provider": "mock"}'
```
