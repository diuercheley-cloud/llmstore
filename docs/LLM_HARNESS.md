# LLM Harness

The LLM Harness is a tool for the governed execution of agentic code tasks within the LLM Inference Stack. It combines a CLI, policy engine, temporary workspaces, local or Docker sandboxing, output sanitization, and automated validation to test coding agent workflows with reduced operational risk.

## Overview

- Run individual code tasks via `llm-harness code`.
- Run batches of scenarios via `llm-harness code-batch`.
- Run evaluation suites with LLM-as-a-judge via `llm-harness eval`.
- Maintain local environment health via `llm-harness health` and `llm-harness security`.
- Centralize security rules in `scripts/llm_harness/policy.py`.
- Generate detailed reports and artifacts in `artifacts/llm_harness/`.

## Cursor-like IDE Features

The harness also exposes a Cursor-style CLI surface for IDE-adjacent workflows:

- `chat`: governed chat with file references, memory, rules, and cached docs context.
- `edit-inline`: inline editing with diff preview, dry-run, and policy-gated patching.
- `index` and `docs`: repository indexing plus external documentation caching.
- `code --image`: multimodal task input for screenshots and images.
- `complete`: fill-in-the-middle code completion suggestions.
- `fix-error` and `terminal`: stderr diagnosis and repair workflows.
- `ide`: VS Code and Cursor settings/rules import.
- `models`: model profile listing and profile smoke tests.

Examples:

```bash
llm-harness chat --provider stub --allow-stub-code-agent --message "Review @file:scripts/llm_harness/cli.py"
llm-harness chat --provider stub --allow-stub-code-agent --message "Summarize @scripts/llm_harness and @selection:scripts/llm_harness/cli.py:1-40"
llm-harness edit-inline scripts/llm_harness/cli.py --range 1:20 --instruction "Tighten help text" --dry-run
llm-harness code --provider stub --allow-stub-code-agent --image screenshot.png --task "Explain the UI issue in this screenshot"
llm-harness complete scripts/llm_harness/cli.py --line 20 --column 4 --provider stub --allow-stub-code-agent
llm-harness fix-error --from-file artifacts/llm_harness/error.log --dry-run --provider stub --allow-stub-code-agent
llm-harness terminal diagnose --stderr-file artifacts/llm_harness/stderr.log
llm-harness terminal suggest --stderr-file artifacts/llm_harness/stderr.log --provider stub --allow-stub-code-agent
llm-harness ide import-vscode --path .
llm-harness ide show-config
llm-harness models list
llm-harness models test local-qwen
```

Model profiles can be declared in `.harness.yaml` and selected with `--model-profile` or by task routing:

```yaml
models:
  default: local-qwen
  profiles:
    local-qwen:
      provider: local-openai-compatible
      model: nvidia/nemotron-3-nano-4b
      base_url: http://192.168.101.1:1234/v1
    cloud-fast:
      provider: openai-compatible
      model: gpt-4o-mini
  routing:
    chat: local-qwen
    completion: local-qwen
    inline-edit: local-qwen
```

Language-aware helpers currently cover Python, JavaScript, TypeScript, Java, and C# for detection, diagnostics hints, indexing fallback, and prompt metadata.

## Installation

### Dependencies

The harness requires the following Python packages:
- `httpx>=0.27`
- `pyyaml>=6.0`
- `pydantic>=2.0`

Development dependencies:
- `pytest`, `pytest-asyncio`, `ruff`, `mypy`

### Setup

From the root of the repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

After installation, you can use the `llm-harness` command or run it as a module:

```bash
llm-harness --help
# OR
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli --help
```

## CLI Usage

The main entry point is `llm-harness`.

```bash
usage: llm-harness [-h] [--config CONFIG] [--debug] {health,code,code-batch,security,eval} ...

LLM Harness CLI

positional arguments:
  {health,code,code-batch,security,eval}
                        Commands
    health              Check harness health
    code                Run single coding task
    code-batch          Run batch of coding tasks
    security            Run security audit
    eval                Run evaluation suite

options:
  -h, --help            show this help message and exit
  --config CONFIG       Path to config file
  --debug               Show verbose stack traces on error
```

### Health Check

To verify your local environment:

```bash
llm-harness health --local-only
```

Example output:
```text
Harness Health: healthy
  python_version: OK
  git_available: OK
  pytest_available: OK
  venv_active: OK
```

## Execution Modes

### Code Mode

Recommended for executing a single task.

```bash
llm-harness code --task "Fix bug in parser.py" --agent-id default-coder
```

Key features:
- Loads configuration with precedence: `CLI > env > file > defaults`.
- Auto-selects provider based on environment (e.g., `OPENAI_API_KEY`).
- Streams progress events to stdout.

### Code-Batch Mode

For running multiple scenarios defined in a JSON file.

```bash
llm-harness code-batch --file scenarios.json --concurrency 2
```

Example `scenarios.json`:
```json
[
  {
    "name": "auth-fix",
    "task": "Fix failing auth tests",
    "agent_id": "default-coder"
  },
  {
    "name": "docs-update",
    "task": "Update README examples"
  }
]
```

### Eval Mode

Run evaluation suites with advanced scoring and optional LLM-as-a-judge.

```bash
llm-harness eval --suite examples/llm_harness/evals/basic_python_fix.eval_suite.json --judge disabled --track
```

#### How to Run an Eval Suite
To run a suite using the simulated `stub` provider (for infrastructure testing):
```bash
llm-harness eval --suite examples/llm_harness/evals/cli_smoke.eval_suite.json --provider stub --allow-stub-code-agent
```

To run with a real model:
```bash
export OPENAI_API_KEY=your_key
llm-harness eval --suite examples/llm_harness/evals/basic_python_fix.eval_suite.json --provider openai-compatible --model gpt-4o
```

#### How to Create a New Suite
Evaluation suites are JSON files defined by the following schema:
- `name`: String, the suite name.
- `description`: String, what the suite tests.
- `cases`: A list of objects containing:
  - `id`: Unique identifier for the case.
  - `task`: The prompt given to the agent.
  - `input_files`: (Optional) Map of filename to content to pre-populate the workspace.
  - `expected_files`: (Optional) Map of filename to content to verify after execution.
  - `test_command`: (Optional) Shell command to run to verify success (exit code 0 means success).
  - `expected_stdout`: (Optional) String that must be present in the test command output.
  - `tags`: (Optional) List of strings for filtering.

Example Case:
```json
{
  "id": "fix-bug",
  "task": "Fix the bug in main.py",
  "input_files": { "main.py": "print('bug')" },
  "test_command": "python3 main.py | grep 'fixed'"
}
```

## Providers

The harness supports multiple LLM providers:

- **stub**: Simulated execution for infrastructure testing. Requires `--allow-stub-code-agent`.
- **openai-compatible**: Connects to any OpenAI-compatible API (e.g., vLLM, Ollama, LM Studio).
- **anthropic**: Integration with Anthropic Claude models.
- **google**: Integration with Google Gemini models.
- **control-plane**: Delegates execution to the LLM Inference Stack control plane.

### OpenAI-Compatible Setup

```bash
export OPENAI_API_KEY=your_api_key
export LLM_BASE_URL=http://localhost:18080/v1
llm-harness code --task "Test task" --provider openai-compatible --model gpt-4o-mini
```

### LM Studio Setup

Use `local-openai-compatible` for LM Studio and other local OpenAI-compatible servers.

```bash
export LLM_HARNESS_LOCAL_BASE_URL="http://127.0.0.1:1234/v1"
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli health \
  --provider local-openai-compatible \
  --base-url "$LLM_HARNESS_LOCAL_BASE_URL"

PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code \
  --provider local-openai-compatible \
  --base-url "$LLM_HARNESS_LOCAL_BASE_URL" \
  --model qwen/qwen3.6-35b-a3b \
  --local-model-timeout 300 \
  --stream \
  --tool-calling auto \
  --approval-policy interactive \
  --task "Validate the harness with LM Studio"
```

Behavior for local providers:
- `OPENAI_API_KEY` is not required.
- `response_format=json_object` is disabled for LM Studio-style endpoints.
- If `--model` is omitted, the harness reads `/v1/models` and auto-selects the first model.
- If `--model` is provided, the harness validates it against the model catalog before execution.
- Streaming is enabled by default when the base URL points to `localhost`, `127.0.0.1`, or `host.docker.internal`.
- Local providers default to a `300s` request timeout and can retry once with a larger timeout via `--auto-increase-timeout`.
- `--tool-calling auto` is conservative for local providers and defaults to JSON actions unless `supports_native_tool_calling=true` AND `--allow-native-tools-for-local` is set.
- `json` keeps the legacy action JSON behavior and is the safest default for LM Studio-style backends.
- `native` forces native `tool_calls`. If the provider fails the native capability probe, execution fails with a descriptive error.
- `--allow-native-tools-for-local` (or `LLM_HARNESS_ALLOW_NATIVE_TOOLS_FOR_LOCAL=1`) explicitly enables native tools for local providers in `auto` mode when supported.
- `health` reports `available_models`, `selected_model`, `supports_response_format`, `supports_native_tool_calling`, and `native_tool_calling_probe` details.
- Capability probe results are cached for 300s (configurable via `--capability-cache-ttl-seconds`) to avoid redundant expensive probes. Caching is per provider, base URL, and model.
- Health output indicates `capability_probe_cache_hit=true` when using cached results.
- Run reports include `final_tool_calling_mode` in `_provider_meta` to verify the decision.
- Malformed `tool_calls` in `native` mode result in a `schema_validation_failed` error and do not execute partially. Fallback to JSON is only permitted in `auto` mode.

### Using LM Studio / local OpenAI-compatible models

Recommended command:

```bash
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code \
  --provider local-openai-compatible \
  --base-url http://127.0.0.1:1234/v1 \
  --model qwen/qwen3.6-35b-a3b \
  --local-model-timeout 300 \
  --auto-increase-timeout \
  --stream \
  --tool-calling native \
  --approval-policy interactive \
  --task "Create SMOKE_TEST.md to confirm write_file works"
```

Smoke test expectations:
- The model can create `SMOKE_TEST.md` through `write_file`.
- The harness accepts native `tool_calls` when the local server supports them.
- If the local server returns plain conversational text plus JSON, the harness extracts the first schema-valid action JSON.
- If the local server rejects multi-turn history or `tool_calls` with `HTTP 400`, the harness retries once with simplified text-only history, disables streaming for the retry, and omits `tools`.
- If the local server returns `200 OK` but still produces empty or schema-incompatible action content, the harness retries once in a stricter JSON-compatible mode.
- After a `final` action executes, the harness terminates the run immediately and blocks any extra LLM calls.
- Reports include `time_to_first_action_ms`, `time_to_final_ms`, and `post_final_llm_calls_blocked` for local debugging.

If LM Studio is not running, skip the live smoke test and use:

```bash
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli health --local-only
```

### Anthropic Setup

```bash
export ANTHROPIC_API_KEY=your_api_key
llm-harness code --task "Test task" --provider anthropic --model claude-3-5-sonnet-20241022
```

Anthropic multimodal support: When `--multimodal` is enabled, image content blocks are automatically converted from the standard `image_url` format to Anthropic's native `{"type": "image", "source": {"type": "base64", "media_type": "...", "data": "..."}}` format.

### Google Setup

```bash
export GOOGLE_API_KEY=your_api_key
llm-harness code --task "Test task" --provider google --model gemini-1.5-pro
```

Google multimodal support: When `--multimodal` is enabled, image content blocks are automatically converted from the standard `image_url` format to Google's `{"inline_data": {"mime_type": "...", "data": "..."}}` format in `parts`.

### Control-Plane Setup

```bash
llm-harness code --task "Refactor module" --provider control-plane --base-url http://control-plane:8080
```

## Configuration File

The harness automatically looks for `.harness.yaml`, `.harness.yml`, or `harness.toml` in the current directory.

Example `.harness.yaml`:
```yaml
code_agent: default-coder
model: gpt-4o-mini
base_url: http://localhost:18080
sandbox: true
docker_image: python:3.12-slim
self_heal: true
test_command: pytest
max_steps: 10
```

## Sandbox (Local vs Docker)

- **Local Sandbox** (`--no-sandbox`): Executes commands directly in a temporary local directory. Fast but less isolated.
- **Docker Sandbox** (`--sandbox`): Executes commands inside a Docker container.
  - Mounts the workspace via volumes.
  - Disables network access (`--network none`).
  - Enforces resource limits (CPU, memory, PIDs).

### Cross-Platform Support

The LLM Harness is designed to be cross-platform, supporting Linux, macOS, and Windows (including WSL).

| Platform | Local Sandbox | Docker Sandbox | Signal Handling |
| --- | --- | --- | --- |
| **Linux** | Full support | Full support | Full (Process Groups) |
| **WSL** | Full support | Full support | Full (Process Groups) |
| **macOS** | Full support | Full support | Full (Process Groups) |
| **Windows** | Limited isolation | Supported (via Docker Desktop) | Limited (Basic signals only) |

#### Platform-Specific Notes

- **Windows**: Local sandbox isolation is limited as Windows does not natively support process groups in the same way Unix does. Command timeouts are handled via `process.kill()`, which may leave orphaned child processes if the command spawns sub-processes. For strong isolation on Windows, using the **Docker Sandbox** is highly recommended.
- **Docker**: Requires Docker to be installed and running on the host machine. On Windows and macOS, ensure Docker Desktop is configured to allow volume mounting for the temporary workspace directories.
- **Signal Handling**: On Unix-like systems (Linux, macOS, WSL), the harness uses process groups (`os.setsid`) to ensure that all child processes are terminated when a command times out or the harness is interrupted.

```bash
llm-harness code --task "Run unsafe code" --sandbox --docker-image python:3.12-slim
```

## Advanced Features

### Context Window Management
The harness automatically manages the context window to prevent exceeding model limits.
- **Preservation**: Critical messages like the system prompt, original task, and latest errors are always kept.
- **Pruning**: Older history is removed using a sliding window.
- **Summarization**: Large tool results are truncated or summarized if a hook is provided.

### Response Schema Validation
Agent actions are strictly validated against a Pydantic schema:
- **Supported Actions**: `plan`, `read_file`, `apply_patch`, `run_shell`, `run_tests`, `parallel`, `final`.
- **Validation**: Rejects invalid JSON or malformed payloads before execution.
- **Parallelism**: Allows read-only actions to be executed concurrently.

### Tokenizer and Budget Planning
- **Token Counting**: Uses `tiktoken` (if available) or a character-based heuristic.
- **Budgeting**: Enforces `max_tokens` limits and reserves space for completions.
- **Metrics**: Tracks `prompt_tokens`, `completion_tokens`, and `total_tokens`.

### Cache TTL and Eviction
- **Expiration**: Entries can have a configurable `ttl_seconds`.
- **Eviction**: Enforces `max_entries` using an LRU-like policy.
- **Side Effects**: Side-effect-heavy actions (like `apply_patch`) are not cached.

### Memory Rotation and Compression
- **Rotation**: Memory files (`runs.jsonl`) are rotated when they exceed `memory_max_file_mb`.
- **Compression**: Rotated files are automatically compressed using GZIP.
- **Retention**: Old memory files are purged after `memory_retention_days`.

### Cost Tracking
The harness estimates the cost of each run based on the model and token usage.
```bash
llm-harness code --task "Fix bug" --max-cost-per-run 0.50 --pricing-file custom_pricing.json
```

### Internal Parallelism
Read-only actions (read_file, grep, ast_search, etc.) can be executed in parallel to speed up execution.
```bash
llm-harness code --task "Analyze codebase" --max-parallel-actions 4
```

### Persistent Memory
The harness maintains a local memory of previous runs to provide context to the agent, improving its decision-making over time.
```bash
llm-harness code --task "Continue previous work" --memory local --memory-dir .my_memory
```

### Multi-Agent Orchestration
Use a Planner-Coder-Reviewer flow for more robust task completion.
```bash
llm-harness code --task "Complex refactoring" --agent-mode planner-coder-reviewer
```

### Action Approval
Control which actions the agent can perform with interactive or automated approval.
```bash
llm-harness code --task "Dangerous cleanup" --approval-mode interactive
```

### Checkpoint and Resume
Resume interrupted runs from the last successful step.
```bash
llm-harness code --resume 20260603_120000
```

### Streaming
Enable real-time response streaming from the LLM provider.
```bash
llm-harness code --task "Long task" --stream
```

## Extended Platform Capabilities

### 1. API Server Mode
The harness can be run in server mode exposing a REST API to manage agent runs, list providers, list tools, and execute benchmarks.

Start the server:
```bash
llm-harness server --host 127.0.0.1 --port 8765
```

Optional Token Authentication:
```bash
# Set server API key in env
export MY_SERVER_API_KEY="my-super-secret-token"
# Start server requiring auth header
llm-harness server --api-key-env MY_SERVER_API_KEY
```

Endpoints exposed:
- `GET /health`: Health status.
- `POST /runs`: Start an agentic coding loop run.
- `GET /runs/{run_id}`: Check run status/result.
- `GET /runs/{run_id}/events`: SSE event stream for live updates.
- `POST /runs/{run_id}/cancel`: Cancel a running task.
- `GET /providers`: List registered providers.
- `GET /tools`: List active tools.
- `GET /evals`: List local eval suites.
- `POST /evals/run`: Start a batch evaluation suite.

### 2. Plugin System
Extenders can add custom tools, LLM providers, scorers, policy rules, and prompt templates.

Manage plugins via CLI:
```bash
# List loaded plugins
llm-harness plugins list --enable-plugins

# Validate plugin registry configurations
llm-harness plugins validate --enable-plugins
```

Plugins can be discovered automatically through Python packaging `entry_points` or placed dynamically inside the local `plugins.d/` directory.

Security guidelines:
- Plugins are disabled by default (safe mode).
- Pass `--enable-plugins` explicitly to discover and load external plugins.
- Core tools are protected against overriding unless the `--allow-overwrite` flag is explicitly set.

### 3. MCP Client Integration
The Model Context Protocol (MCP) client allows agents to load and invoke external tools hosted by separate MCP servers.

Configure MCP servers in `.harness.yaml`:
```yaml
mcp:
  enabled: true
  servers:
    - name: filesystem
      command: node
      args: ["/path/to/mcp-server-filesystem.js", "/workspace"]
```

Security and validation:
- MCP tools are disabled by default. Set `allow_mcp_tools=true` in `PolicyEngine` (or configuration) to enable them.
- All MCP tools calls pass through the `PolicyEngine` (e.g. boundary path checking, shell filtering).
- Input and output payloads are sanitised to prevent leaking secrets.

### 4. Standard Benchmarks
Standard mini benchmark suites (e.g. HumanEval, SWE-bench) can be run locally using static files, removing any external network dependencies.

Run benchmark suites:
```bash
# Run a specific benchmark JSON suite
llm-harness benchmark run --suite examples/llm_harness/benchmarks/humaneval_mini.json

# Compare benchmark results against a baseline
llm-harness benchmark compare --result benchmark_result.json --baseline baseline.json --threshold 0.05
```

### 5. Multi-modal Support
The schema of messages and context is expanded to support text, image, audio, and video content blocks.

Run multimodal tasks:
```bash
# Image input
llm-harness code --image path/to/screenshot.png --task "Fix visual formatting bugs" --multimodal

# Audio input
llm-harness code --audio path/to/recording.mp3 --task "Transcribe and analyze" --multimodal

# Video input
llm-harness code --video path/to/demo.mp4 --task "Describe the video content" --multimodal

# Multiple media types
llm-harness code --image ui.png --audio narration.mp3 --task "Fix UI issue" --multimodal
```

**Provider adapters:**
- **OpenAI-compatible**: Converts `image_url` content blocks natively.
- **Anthropic**: Converts `image_url` blocks to Anthropic's `{"type": "image", "source": {"type": "base64", ...}}` format.
- **Google**: Converts `image_url` blocks to Google's `{"inline_data": {"mime_type": "...", "data": "..."}}` format.
- **Audio/Video**: Content is loaded as base64 and sent as `audio_url`/`video_url` blocks with metadata (`mime_type`, `extension`). The actual processing depends on provider capability.

Governance rules:
- Multimodal inputs are only accepted if the provider/model explicitly supports it (enabled via config or flags).
- Media file paths are resolved against the workspace path and boundary-validated by the `PolicyEngine`.
- Media data and base64 payloads are automatically redacted from logs and execution traces to keep artifacts clean.

### 6. GSM8K-Style Benchmark Adapter
The harness includes a GSM8K-style text reasoning benchmark adapter for evaluating arithmetic reasoning.

```bash
llm-harness benchmark run --suite examples/llm_harness/benchmarks/gsm8k_mini.json
```

The adapter:
- Extracts expected answers from `####` markers in prompt data.
- Predicts answers from model output using regex patterns.
- Normalizes numbers (handles commas, floats, integers).
- Reports `pass@1`, `accuracy`, `solved/failed`, `duration_ms`, `tokens`, and `estimated_cost`.

## Security Policy

The `PolicyEngine` enforces governance rules:
- **Shell Blocking**: Prevents dangerous operators (`;`, `|`, `&&`, etc.) and forbidden commands (`sudo`, `rm -rf /`, `git push`).
- **File Access**: Restricts access to sensitive files like `.env`, `id_rsa`, and `.git`.
- **Patch Validation**: Prevents modification of security-critical files like `policy.py` and `sandbox.py`.

## Secrets Redaction

The `Sanitizer` automatically redacts sensitive information from logs and reports, including:
- Bearer tokens and API keys.
- Passwords in URLs.
- Sensitive query parameters.

## Release Gate

The release gate ensures the harness meets production core standards. It checks for:
- Successful validation (`scripts/validators/validate-llm-harness.sh`).
- Type check completeness.
- Secrets redaction verification.
- Documentation presence.
- **Server Health Gate**: Verify server exposing runs and health endpoints correctly.
- **Plugin Registry Gate**: Verify plugin registration logic and core tool overwrite protection.
- **MCP Client Gate**: Verify MCP configurations and policy validations.
- **Benchmark Mini Gate**: Verify benchmark runner accuracy calculations and regression checks.
- **Multimodal Schema Gate**: Verify context schemas for image support.

To run the release gate manually:
```bash
make release-gate-llm-harness
```

### CI/CD

The LLM Harness has a dedicated CI pipeline defined in `.github/workflows/llm-harness.yml`.

### Pre-commit Hooks

The harness includes a pre-commit configuration to enforce linting (`ruff`), formatting, and static typing (`mypy`) locally before committing changes.

To set up pre-commit:
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```


### Integration Tests with Local LLMs

The harness includes optional integration tests that can be run against real local LLM servers (e.g., Ollama, vLLM, LM Studio). These tests are skipped by default and require specific environment variables.

#### Prerequisites
- A running OpenAI-compatible server (e.g., Ollama with `ollama serve`).
- The model you intend to test must be already pulled/loaded.

#### Running the tests
Set the following environment variables, validate the endpoint, and run the Makefile target:

```bash
export LLM_HARNESS_RUN_LOCAL_LLM_TESTS=1
export LLM_HARNESS_LOCAL_BASE_URL="http://localhost:11434/v1"
export LLM_HARNESS_LOCAL_MODEL="llama3"
export LLM_HARNESS_LOCAL_API_KEY="optional-key"

./scripts/validators/validate-local-llm-harness-env.sh
make integration-local-llm-harness
```

#### Provider-specific examples:
- **Ollama**: `LLM_HARNESS_LOCAL_BASE_URL="http://localhost:11434/v1"`
- **vLLM**: `LLM_HARNESS_LOCAL_BASE_URL="http://localhost:8000/v1"`
- **LM Studio**: `LLM_HARNESS_LOCAL_BASE_URL="http://localhost:1234/v1"`

These tests use the `local-openai-compatible` provider path so they can run without requiring a cloud-style API key.

When using LM Studio interactively, prefer `local-openai-compatible` instead of `openai-compatible`. The local provider avoids the JSON response-format fallback loop and can auto-discover the model list.

### Path Filtering
To optimize CI resources, the harness workflow only runs when changes are detected in:
- `scripts/llm_harness/**`
- `tests/integration/llm_harness/**`
- `scripts/validators/validate-llm-harness.sh`
- `pyproject.toml`
- `docs/LLM_HARNESS.md`
- `examples/llm_harness/**`

### Automated Checks
Every pull request targeting the harness undergoes:
1. **Linting**: Using `ruff`.
2. **Type Checking**: Using `mypy`.
3. **Unit Tests**: Full suite execution via `pytest`.
4. **Health Check**: Operational check via `llm-harness health`.
5. **Release Gate**: Final production-readiness check.

### Manual Benchmarks
Performance benchmarks can be triggered manually via GitHub Actions (Workflow Dispatch) to track execution speed and resource usage regressions.

## Troubleshooting

### Missing `httpx`
Ensure the virtual environment is active and dependencies are installed:
```bash
pip install -e "."
```

### API Key Missing
Use `openai-compatible` for cloud or authenticated endpoints. Use `local-openai-compatible` for LM Studio, Ollama, or other local OpenAI-compatible servers. Local providers do not require `OPENAI_API_KEY`.
```bash
export OPENAI_API_KEY=your_key
```

### Docker Issues
If `--sandbox` fails, check if Docker is running:
```bash
docker info
```

### Stub Agent behavior
The `stub` provider is for **testing infrastructure only**. It will NOT execute real code changes or solve tasks. Always use a real provider for actual work.
