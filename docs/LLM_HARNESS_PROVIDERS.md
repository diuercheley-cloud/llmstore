# LLM Harness Provider Compatibility Matrix

This document provides a matrix of LLM providers supported by the LLM Harness, detailing their required configurations, CLI flags, expected response formats, limitations, and examples.

---

## Provider Overview Matrix

| Provider Name | Key Environment Variables | Core CLI Flags | Response JSON Schema | Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **stub** | None | `--provider stub` | Static mocked response | Simulated only; no real model invocation |
| **openai-compatible** | `OPENAI_API_KEY` (or custom) | `--provider openai-compatible`, `--model`, `--base-url` | Chat completions JSON object | Requires standard OpenAI chat routes |
| **local-openai-compatible**| None (optional API key) | `--provider local-openai-compatible`, `--model`, `--base-url`, `--local-model-timeout`, `--tool-calling`, `--stream` | Chat completions JSON object or native `tool_calls` | Bypasses API key requirements; local targets only |
| **anthropic** | `ANTHROPIC_API_KEY` | `--provider anthropic`, `--model` | Anthropic message schema | Specific system instructions mapping |
| **google** | `GEMINI_API_KEY` (or custom) | `--provider google`, `--model` | Google Gemini API schema | Different payload structure, requires Gemini key header |
| **control-plane** | `OPENAI_API_KEY` (or custom) | `--provider control-plane`, `--base-url`, `--agent-id` | Server Sent Events (SSE) JSON | Heavy dependency on list/stream APIs |

---

## Providers Detail

### 1. Stub (`stub`)
A mock/stub provider used for local sanity testing without hitting external network boundaries.

- **Variables Required**: None.
- **CLI Flags**: `--provider stub`
- **Expected Response Format**:
  A static final action:
  ```json
  {
    "action_type": "final",
    "message": "Task completed (simulated)"
  }
  ```
- **Limitations**: Does not run a real model. Used strictly for integration testing.
- **Example Usage**:
  ```bash
  python3 -m scripts.llm_harness.cli code --provider stub --task "Test Task"
  ```

---

### 2. OpenAI Compatible (`openai-compatible`)
Designed for providers that implement the OpenAI Chat Completions API standard (e.g. OpenAI, Together AI, Groq, etc.).

- **Variables Required**: API key stored in the environment variable specified (default: `OPENAI_API_KEY`).
- **CLI Flags**:
  - `--provider openai-compatible`
  - `--model <model-name>` (e.g. `gpt-4`)
  - `--base-url <url>` (e.g. `https://api.openai.com/v1`)
  - `--api-key-env <env_var>` (optional, defaults to `OPENAI_API_KEY`)
- **Expected Response Format**:
  Standard chat completions schema where the model response is parsed from `choices[0].message.content` as a valid harness action JSON:
  ```json
  {
    "type": "plan|read_file|apply_patch|run_shell|run_tests|final",
    "reason": "Reason for action",
    "payload": {}
  }
  ```
- **Limitations**:
  - The API endpoint must expose standard paths like `/v1/chat/completions`, `/chat/completions`, etc.
  - The model must output parseable JSON matching the harness action format.
- **Example Usage**:
  ```bash
  export OPENAI_API_KEY="your-key"
  python3 -m scripts.llm_harness.cli code \
    --provider openai-compatible \
    --model gpt-4o \
    --base-url https://api.openai.com \
    --task "Fix syntax bug in utils.py"
  ```

---

### 3. Local OpenAI Compatible (`local-openai-compatible`)
Bypasses mandatory API key validations for local tools like Ollama or LM Studio.

- **Variables Required**: None (optional API key can still be passed if needed).
- **CLI Flags**:
  - `--provider local-openai-compatible`
  - `--model <model-name>` (e.g. `qwen/qwen3.6-35b-a3b`)
  - `--base-url <url>` (e.g. `http://localhost:1234/v1`)
  - `--local-model-timeout 300`
  - `--auto-increase-timeout`
  - `--tool-calling auto|native|json`
  - `--allow-native-tools-for-local` to enable native tools for local backends in `auto` mode
  - `--capability-cache-ttl-seconds <seconds>` (default 300)
  - `--supports-tool-calling` for remote OpenAI-compatible providers that expose native tools
  - `--stream` or `--no-stream`
- **Expected Response Format**:
  Same as `openai-compatible`, plus native OpenAI-compatible `tool_calls` when the local server supports them and they are enabled/requested.
- **Native Tool Probing**:
  The `health_check` performs an explicit probe for native `tool_calling` capabilities. 
  - `supports_native_tool_calling`: boolean indicating if the probe succeeded.
  - `native_tool_calling_probe`: detailed results of the probe (status, reason).
  - Probe results are cached to minimize overhead.
- **Limitations**:
  - Designed for `localhost`, `127.0.0.1`, and `host.docker.internal` style endpoints.
  - In `auto` mode, local providers default to JSON actions for stability unless `allow_native_tools_for_local` is true.
  - Executes actions only after a full JSON object or a full `tool_call` is accumulated and schema-validated.
  - Hard-denied policy decisions still block execution even when interactive approval is enabled.
- **Example Usage**:
  ```bash
  python3 -m scripts.llm_harness.cli code \
    --provider local-openai-compatible \
    --model qwen/qwen3.6-35b-a3b \
    --base-url http://127.0.0.1:1234/v1 \
    --local-model-timeout 300 \
    --auto-increase-timeout \
    --tool-calling auto \
    --allow-native-tools-for-local \
    --stream \
    --task "Create SMOKE_TEST.md and validate write_file"
  ```

#### LM Studio Notes

- `http://127.0.0.1:1234/v1` and `http://127.0.0.1:1234/v1/chat/completions` are both accepted.
- In `auto` mode the harness defaults to legacy JSON action extraction for local providers. Use `--allow-native-tools-for-local` to allow native `tool_calls` when the probe confirms support.
- If `--tool-calling native` is used, the harness REQUIRES a successful probe; otherwise it fails with a clear error and troubleshooting suggestions.
- For remote `openai-compatible` endpoints, declare native tools explicitly with `--supports-tool-calling` when the server implements them.
- Capability probes are cached per model/url; use `--capability-cache-ttl-seconds 0` to force re-probe.
- Streaming is enabled by default for local endpoints and emits sanitized `llm.delta` and `llm.completed` events.
- Read timeouts from local models recommend a `300s` timeout and can trigger one retry with the increased timeout when `--auto-increase-timeout` is set.
- If a local endpoint returns `HTTP 400` on a follow-up turn, the harness retries once in a compatibility mode that:
  - simplifies prior assistant/tool messages into plain text,
  - disables streaming for the retry,
  - omits native `tools` and `tool_choice`,
  - preserves schema validation before any action executes.
- Once a `final` action succeeds, the run ends immediately. Subsequent LLM calls are blocked and counted in `post_final_llm_calls_blocked`.
- Reports and event logs expose `time_to_first_action_ms`, `time_to_final_ms`, `llm.local_400_retry`, and `llm.local_retry_mode` to help diagnose LM Studio behavior.
- Reports also include `final_tool_calling_mode` in metadata.

---

### 4. Anthropic (`anthropic`)
Integrates directly with Anthropic's Messages API (Claude).

- **Variables Required**: API key stored in the environment variable specified (default: `ANTHROPIC_API_KEY`).
- **CLI Flags**:
  - `--provider anthropic`
  - `--model <model-name>` (optional, defaults to `claude-3-5-sonnet-20241022`)
  - `--base-url <url>` (optional, falls back to `https://api.anthropic.com`)
  - `--api-key-env <env_var>` (optional, defaults to `ANTHROPIC_API_KEY`)
- **Expected Response Format**:
  Anthropic Messages API response containing `content` text block:
  ```json
  {
    "content": [
      {
        "type": "text",
        "text": "{\"type\":\"plan\",\"reason\":\"checking file\",\"payload\":{}}"
      }
    ],
    "usage": {
      "input_tokens": 10,
      "output_tokens": 20
    }
  }
  ```
- **Limitations**:
  - Translates `system` messages into Anthropic's top-level `system` payload parameter.
  - Automatically expects the model response text to contain valid harness action JSON.
- **Example Usage**:
  ```bash
  export ANTHROPIC_API_KEY="your-api-key"
  python3 -m scripts.llm_harness.cli code \
    --provider anthropic \
    --model claude-3-5-sonnet-20241022 \
    --task "Analyze test failures"
  ```

---

### 5. Google Gemini (`google`)
Integrates directly with Google's Developer API (Gemini).

- **Variables Required**: API key stored in the environment variable specified (default: `GEMINI_API_KEY` or `OPENAI_API_KEY` depending on config).
- **CLI Flags**:
  - `--provider google`
  - `--model <model-name>` (optional, defaults to `gemini-1.5-pro`)
  - `--base-url <url>` (optional, falls back to `https://generativelanguage.googleapis.com`)
  - `--api-key-env <env_var>` (optional, defaults to `OPENAI_API_KEY` if not overridden)
- **Expected Response Format**:
  Gemini generateContent endpoint response containing `candidates[0].content.parts[0].text`:
  ```json
  {
    "candidates": [
      {
        "content": {
          "parts": [
            {
              "text": "{\"type\":\"final\",\"payload\":{\"message\":\"fixed\"}}"
            }
          ]
        }
      }
    ]
  }
  ```
- **Limitations**:
  - Mandates setting `responseMimeType` to `application/json`.
  - Sends the API key via custom `x-goog-api-key` header.
- **Example Usage**:
  ```bash
  export GEMINI_API_KEY="your-gemini-api-key"
  python3 -m scripts.llm_harness.cli code \
    --provider google \
    --model gemini-1.5-pro \
    --api-key-env GEMINI_API_KEY \
    --task "Fix app crash"
  ```

---

### 6. Control Plane (`control-plane`)
Uses a remote Control Plane orchestrator to sync/run coding agents, streaming events via SSE.

- **Variables Required**: API key stored in the environment variable specified (default: `OPENAI_API_KEY`).
- **CLI Flags**:
  - `--provider control-plane`
  - `--base-url <url>` (required, e.g. `http://localhost:8000`)
  - `--agent-id <id>` (optional, defaults to `default`)
- **Expected Response Format**:
  Valid Server-Sent Events (SSE) lines starting with `data:` containing the JSON events of the agent run.
- **Limitations**:
  - Depends on agents already registered on the control plane endpoint.
  - Requires active streaming/SSE compatibility.
- **Example Usage**:
  ```bash
  python3 -m scripts.llm_harness.cli code \
    --provider control-plane \
    --base-url http://localhost:8080 \
    --agent-id test-agent \
    --task "Run test task"
  ```

---

## Multimodal Provider Support

Providers that declare `multimodal: true` in their configuration can receive task descriptions structured as lists of content blocks containing text and images (e.g. screenshot of UI bug).

### Multimodal Providers Configuration
To run a multimodal task, the provider config must explicitly enable multimodal capabilities.

Example `.harness.yaml` config:
```yaml
provider: openai-compatible
model: gpt-4o
multimodal: true
```

Or via CLI overrides:
```bash
llm-harness code --image path/to/screenshot.png --task "Fix visual bug" --multimodal
```

### Compatible Providers
1. **openai-compatible**:
   When `multimodal: true` is configured, messages will contain list content blocks formatted according to the OpenAI multimodal schema:
   ```json
   {
     "role": "user",
     "content": [
       {"type": "text", "text": "Task description"},
       {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
     ]
   }
   ```
2. **stub**:
   Accepts multimodal input when `--multimodal` is explicitly configured. Fails with a clean `ValueError` if multimodal is disabled.

### Path Resolution & Redaction
- Image paths must resolve within the target workspace directory. Paths outside the workspace are blocked by the `PolicyEngine` to enforce isolation.
- To prevent secrets leaks and excessively large traces/reports, base64 image strings are automatically replaced by `[REDACTED_IMAGE_BASE64]` inside reports, event metrics, and telemetry spans.
