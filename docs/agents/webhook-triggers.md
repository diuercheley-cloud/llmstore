# Webhook Triggers and Security

Webhook triggers allow external systems (e.g. GitHub, GitLab, custom HTTP clients) to initiate agent runs. Because webhook endpoints are exposed publicly, strict signature validation is required.

## Request Validation Protocol

1. When a webhook trigger is created, a shared secret is configured in its config dictionary (e.g. `secret`).
2. The client must compute a HMAC-SHA256 signature of the serialized JSON payload body using the shared secret.
3. The signature must be sent in the header specified by `signature_header` (defaults to `X-Agent-Signature`).
4. The public route `/agents/events/webhooks/{trigger_id}` performs a constant-time comparison (`hmac.compare_digest`) between the client signature and the computed signature.
5. If signatures do not match, the request is rejected with `403 Forbidden`.

## Example Webhook Invocation

### Request Header
```http
POST /agents/events/webhooks/7bce1549-603c-4362-83d4-6b8711280a00 HTTP/1.1
Host: gateway.llm.stack
Content-Type: application/json
X-Agent-Signature: f9a2fa37ce46409a9c13d7ea31308937...
```

### JSON Body
```json
{
  "input_text": "Please analyze this alert",
  "alert_type": "high_cpu",
  "system": "database-production"
}
```
