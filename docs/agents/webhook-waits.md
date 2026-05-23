# Webhook Waits

Workflows can pause execution and wait for an external HTTP callback.

## Usage

1. A workflow registers a wait condition for a specific `webhook_id`.
2. The workflow enters `waiting_webhook` (or waits for a signal).
3. An external system calls `POST /agents/workflows/webhooks/{webhook_id}`.
4. The engine converts the webhook payload into a workflow signal.
5. The workflow wakes up and continues processing.

## Security

Webhooks should ideally use signed payloads or secret tokens, although this prototype uses a simple ID-based matching.
