import argparse


def add_config_args(parser: argparse.ArgumentParser):
    """Arguments related to global configuration and debug."""
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--debug", action="store_true", help="Show verbose stack traces on error")

def add_provider_args(
    parser: argparse.ArgumentParser, default_code_agent=None, default_allow_stub=False
):
    """Arguments related to provider selection and settings."""
    parser.add_argument(
        "--code-agent",
        "--provider",
        dest="code_agent",
        choices=[
            "stub",
            "openai-compatible",
            "local-openai-compatible",
            "anthropic",
            "google",
            "control-plane",
        ],
        default=default_code_agent,
        help="Provider for the code agent",
    )
    parser.add_argument("--model", help="LLM model to use")
    parser.add_argument("--base-url", help="Base URL for provider")
    parser.add_argument("--api-key-env", help="Environment variable containing the API key")
    parser.add_argument("--timeout", type=float, help="Timeout in seconds for API calls")
    parser.add_argument(
        "--local-model-timeout",
        type=float,
        help="Timeout in seconds for local models and localhost-compatible providers",
    )
    parser.add_argument(
        "--auto-increase-timeout",
        action="store_true",
        help="Retry one time with a higher timeout after a local-model read timeout",
    )
    parser.add_argument("--max-retries", type=int, help="Maximum number of retries for API calls")
    parser.add_argument("--stream", action="store_true", help="Enable streaming for LLM responses")
    parser.add_argument(
        "--no-stream",
        action="store_false",
        dest="stream",
        help="Disable streaming",
    )
    parser.add_argument(
        "--stream-local-default",
        type=lambda value: str(value).lower() in {"1", "true", "yes", "on"},
        help="Enable streaming by default for local models",
    )
    parser.add_argument(
        "--verbose-stream",
        action="store_true",
        help="Print sanitized streamed deltas in the CLI",
    )
    parser.add_argument(
        "--tool-calling",
        choices=["auto", "native", "json"],
        help="How to invoke tools for compatible providers",
    )
    parser.add_argument(
        "--supports-tool-calling",
        action="store_true",
        help="Declare that the selected provider supports OpenAI-compatible tool calls",
    )
    parser.add_argument(
        "--allow-stub-code-agent",
        action="store_true",
        default=default_allow_stub,
        help="Explicitly allow using the stub agent",
    )
    parser.add_argument(
        "--multimodal",
        action="store_true",
        help="Enable multimodal capabilities for the provider",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        help="Maximum tokens for LLM response (required for reasoning models like Qwen3)",
    )

def add_sandbox_args(parser: argparse.ArgumentParser):
    """Arguments related to docker sandbox execution."""
    parser.add_argument("--sandbox", action="store_true", default=None, help="Enable sandbox")
    parser.add_argument("--docker-image", help="Docker image for sandbox")
    parser.add_argument(
        "--workspace-mount-path",
        help="Workspace mount path inside docker container",
    )
    parser.add_argument(
        "--temp-base-dir",
        help="Temporary base directory for workspace creation",
    )
    parser.add_argument(
        "--sandbox-network",
        choices=["none", "host", "proxy"],
        default="none",
        help="Network mode for sandbox",
    )
    parser.add_argument("--proxy-url", help="Proxy URL for sandbox network")

def add_policy_args(parser: argparse.ArgumentParser, default_self_heal=None):
    """Arguments related to self-healing policy and execution behaviors."""
    parser.add_argument(
        "--no-self-heal",
        action="store_false",
        dest="self_heal",
        default=default_self_heal,
        help="Disable self-heal",
    )
    parser.add_argument(
        "--allow-test-short-circuit",
        action="store_true",
        help="Allow short-circuiting task execution for tests",
    )

def add_report_args(parser: argparse.ArgumentParser):
    """Arguments related to output generation and report configuration."""
    parser.add_argument(
        "--report-output-path",
        help="Report output directory",
    )
    parser.add_argument(
        "--max-output-chars",
        type=int,
        help="Maximum characters of shell tool output before truncation",
    )

def add_cache_args(parser: argparse.ArgumentParser):
    """Arguments related to prompt/response caching."""
    parser.add_argument(
        "--cache",
        choices=["disabled", "read-only", "llm"],
        help="Cache mode",
    )
    parser.add_argument("--cache-dir", help="Cache directory")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache")

def add_execution_args(parser: argparse.ArgumentParser, default_loop_timeout=None):
    """Execution control arguments like timeouts."""
    parser.add_argument(
        "--loop-timeout",
        type=int,
        default=default_loop_timeout,
        help="Timeout in seconds for execution loop",
    )

def add_pricing_args(parser: argparse.ArgumentParser):
    """Arguments related to pricing and usage limits."""
    parser.add_argument("--pricing-file", help="Path to pricing JSON file")
    parser.add_argument("--max-cost-per-run", type=float, help="Maximum allowed cost per run")
    parser.add_argument("--max-tokens-per-run", type=int, help="Maximum allowed tokens per run")

def add_memory_args(parser: argparse.ArgumentParser):
    """Arguments related to persistent memory."""
    parser.add_argument(
        "--memory",
        choices=["disabled", "local"],
        default="local",
        help="Memory mode",
    )
    parser.add_argument("--memory-dir", help="Memory directory")
    parser.add_argument(
        "--memory-retention-days",
        type=int,
        help="How many days to keep memory entries",
    )

def add_agent_args(parser: argparse.ArgumentParser):
    """Arguments related to agent orchestration."""
    parser.add_argument(
        "--agent-mode",
        choices=["single", "planner-coder-reviewer"],
        default="single",
        help="Agent orchestration mode",
    )

def add_approval_args(parser: argparse.ArgumentParser):
    """Arguments related to action approval."""
    parser.add_argument(
        "--approval-mode",
        choices=["auto", "deny", "interactive", "non_interactive"],
        default="auto",
        help="Action approval mode",
    )
    parser.add_argument(
        "--approval-policy",
        dest="approval_mode",
        choices=["auto", "deny", "interactive", "non_interactive"],
        help="Alias for --approval-mode",
    )
    parser.add_argument(
        "--approval-default",
        choices=["allow", "deny"],
        default="deny",
        help="Default policy for non-interactive approval",
    )
    parser.add_argument(
        "--edit-action-before-run",
        action="store_true",
        help="Allow editing action payloads before approval in interactive mode",
    )

def add_checkpoint_args(parser: argparse.ArgumentParser):
    """Arguments related to checkpoint/resume."""
    parser.add_argument("--checkpoint-dir", help="Checkpoint directory")
    parser.add_argument("--resume", help="Run ID to resume from checkpoint")
    parser.add_argument(
        "--checkpoint-every-step",
        action="store_true",
        help="Automatically save checkpoint after each step",
    )

def add_tracking_args(parser: argparse.ArgumentParser):
    """Arguments related to experiment tracking."""
    parser.add_argument(
        "--experiment-tracker",
        choices=["local", "mlflow", "disabled"],
        default="local",
        help="Experiment tracker to use",
    )
    parser.add_argument("--mlflow-tracking-uri", help="MLflow tracking URI")
    parser.add_argument("--mlflow-experiment", help="MLflow experiment name")

def add_eval_args(parser: argparse.ArgumentParser):
    """Arguments specific to the evaluation commands."""
    parser.add_argument(
        "--max-steps", type=int, default=10, help="Max steps per case"
    )
    parser.add_argument(
        "--report",
        choices=["json", "markdown", "both"],
        default="json",
        help="Report format",
    )
    parser.add_argument(
        "--output",
        default="artifacts/llm_harness",
        help="Output directory for reports",
    )
    parser.add_argument(
        "--judge",
        choices=["disabled", "openai-compatible", "local-openai-compatible"],
        default="disabled",
        help="Judge provider for LLM-as-a-judge evaluation",
    )
    parser.add_argument("--judge-model", help="Model for the judge LLM")
    parser.add_argument("--judge-base-url", help="Base URL for judge provider")
    parser.add_argument(
        "--judge-api-key-env",
        help="Environment variable for judge API key",
    )
    parser.add_argument(
        "--judge-threshold",
        type=float,
        default=0.75,
        help="Minimum judge score to pass (0.0 to 1.0)",
    )
    parser.add_argument(
        "--track",
        action="store_true",
        help="Enable local experiment tracking",
    )
    parser.add_argument(
        "--track-dir",
        default="artifacts/evals/runs",
        help="Directory for experiment tracking runs",
    )
    parser.add_argument(
        "--prompt-version",
        default="",
        help="Prompt version identifier for tracking",
    )
    parser.add_argument(
        "--prompt-hash",
        default="",
        help="Prompt hash for tracking",
    )
    parser.add_argument(
        "--policy-preset",
        default="",
        help="Policy preset name for tracking",
    )
