# Speech-To-Text Service

The speech-to-text service provides transcription capabilities for audio files. It allows agents to process audio records safely, capturing metadata such as language confidence and duration while respecting raw audio storage policies.

## Endpoint

`POST /v1/multimodal/speech-to-text`

### Request Parameters (Multipart/Form)

* `audio_file` (file, required): Uploaded audio file (e.g., WAV, MP3).
* `language` (string, optional): Target language code (e.g., `"en"`, `"pt"`). If omitted, the service attempts auto-detection.
* `provider` (string, optional, default: `"mock"`): Transcription engine. Options: `"mock"`, `"whisper"`.

### Response Format (JSON)

```json
{
  "text": "Hello, this is a mock transcription of the uploaded audio file.",
  "duration_seconds": 12.5,
  "language": "en",
  "confidence": 0.95,
  "asset_id": "c1f710ad-542e-4b68-b772-c5188f612d4a"
}
```

## Security & Storage Policies

1. **Feature Flag Guard**: Access to the endpoint is blocked with a `403 Forbidden` error if `SPEECH_TO_TEXT_ENABLED=false`.
2. **Raw Audio Retention**: To protect user privacy, raw audio files are **deleted immediately** after transcription processing by default unless a tenant-specific audit or compliance policy explicitly mandates archiving. If storage is skipped, only metadata (transcription text, confidence, duration) is preserved, and the `asset_id` returned will map to `null` or a skipped status.
3. **Budget/Quota Enforcements**: Limits are enforced per client/tenant. When a tenant exceeds their monthly budget (capped at $10.00 in production), requests are blocked with a `429 Too Many Requests`.

## Provider Options

* **Mock Provider (default)**: Returns a mock transcription, detects a default language, and registers estimated confidence and duration based on the input file metadata.
* **Whisper Provider (optional)**: Performs local or remote Whisper API transcription when fully configured and enabled.

## Usage Example

### Python

```python
import httpx

headers = {"Authorization": "Bearer sk-your-api-key-here.val"}
files = {"audio_file": open("voice_note.wav", "rb")}
data = {"language": "en", "provider": "mock"}

response = httpx.post("http://localhost:8000/v1/multimodal/speech-to-text", headers=headers, files=files, data=data)
print(response.json())
```

### Curl

```bash
curl -X POST http://localhost:8000/v1/multimodal/speech-to-text \
  -H "Authorization: Bearer sk-your-api-key-here.val" \
  -F "audio_file=@voice_note.wav" \
  -F "provider=mock"
```
