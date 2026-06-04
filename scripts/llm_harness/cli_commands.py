import asyncio
import json
import os
import sys
import time
from typing import Any

from .cache import resolve_cache_mode
from .health import HealthCheck
from .sanitizer import Sanitizer


def _print_progress_event(event):
    print(
        f"[{event['step']}] {event['event']} {event['action_type']} "
        f"status={event['status']} msg={event['message']}"
    )

def _resolve_code_agent(args) -> str:
    code_agent = getattr(args, "code_agent", None) or getattr(args, "provider", None)
    if code_agent:
        return code_agent
    allow_stub = getattr(args, "allow_stub_code_agent", False)
    if allow_stub:
        return "stub"
    return "openai-compatible"


def build_config_overrides(args) -> dict[str, Any]:
    return {
        "config": getattr(args, "config", None),
        "code_agent": getattr(args, "agent_id", None),
        "provider": _resolve_code_agent(args),
        "model": getattr(args, "model", None),
        "base_url": getattr(args, "base_url", None),
        "sandbox": getattr(args, "sandbox", None),
        "docker_image": getattr(args, "docker_image", None),
        "self_heal": getattr(args, "self_heal", None),
        "api_key_env": getattr(args, "api_key_env", None),
        "timeout": getattr(args, "timeout", None),
        "local_model_timeout": getattr(args, "local_model_timeout", None),
        "auto_increase_timeout": getattr(args, "auto_increase_timeout", None),
        "max_retries": getattr(args, "max_retries", None),
        "stream": getattr(args, "stream", None),
        "stream_local_default": getattr(args, "stream_local_default", None),
        "verbose_stream": getattr(args, "verbose_stream", None),
        "tool_calling": getattr(args, "tool_calling", None),
        "supports_tool_calling": getattr(args, "supports_tool_calling", None),
        "workspace_mount_path": getattr(args, "workspace_mount_path", None),
        "temp_base_dir": getattr(args, "temp_base_dir", None),
        "sandbox_network": getattr(args, "sandbox_network", None),
        "proxy_url": getattr(args, "proxy_url", None),
        "loop_timeout": getattr(args, "loop_timeout", None),
        "max_output_chars": getattr(args, "max_output_chars", None),
        "report_output_path": getattr(args, "report_output_path", None),
        "cache": resolve_cache_mode(getattr(args, "cache", None), getattr(args, "no_cache", False)),
        "cache_dir": getattr(args, "cache_dir", None),
        "pricing_file": getattr(args, "pricing_file", None),
        "max_cost_per_run": getattr(args, "max_cost_per_run", None),
        "max_tokens_per_run": getattr(args, "max_tokens_per_run", None),
        "memory": getattr(args, "memory", None),
        "memory_dir": getattr(args, "memory_dir", None),
        "memory_retention_days": getattr(args, "memory_retention_days", None),
        "agent_mode": getattr(args, "agent_mode", None),
        "approval_mode": getattr(args, "approval_mode", None),
        "approval_default": getattr(args, "approval_default", None),
        "edit_action_before_run": getattr(args, "edit_action_before_run", None),
        "checkpoint_dir": getattr(args, "checkpoint_dir", None),
        "checkpoint_every_step": getattr(args, "checkpoint_every_step", None),
        "multimodal": getattr(args, "multimodal", None),
        "max_tokens": getattr(args, "max_tokens", None),
    }

def build_provider_config(args) -> dict[str, Any]:
    return {
        "provider": _resolve_code_agent(args),
        "model": getattr(args, "model", None),
        "base_url": getattr(args, "base_url", None),
        "api_key_env": getattr(args, "api_key_env", None),
        "timeout": getattr(args, "timeout", None),
        "local_model_timeout": getattr(args, "local_model_timeout", None),
        "auto_increase_timeout": getattr(args, "auto_increase_timeout", None),
        "max_retries": getattr(args, "max_retries", None),
        "stream": getattr(args, "stream", None),
        "stream_local_default": getattr(args, "stream_local_default", None),
        "verbose_stream": getattr(args, "verbose_stream", None),
        "tool_calling": getattr(args, "tool_calling", None),
        "supports_tool_calling": getattr(args, "supports_tool_calling", None),
        "multimodal": getattr(args, "multimodal", None),
        "max_tokens": getattr(args, "max_tokens", None),
    }

def build_sandbox_config(args) -> dict[str, Any]:
    return {
        "sandbox": getattr(args, "sandbox", None),
        "docker_image": getattr(args, "docker_image", None),
        "workspace_mount_path": getattr(args, "workspace_mount_path", None),
        "temp_base_dir": getattr(args, "temp_base_dir", None),
        "sandbox_network": getattr(args, "sandbox_network", None),
        "proxy_url": getattr(args, "proxy_url", None),
    }

def _validate_provider_settings(provider: str, config, allow_stub: bool):
    if provider == "stub":
        if not allow_stub:
            raise ValueError(
                "Stub provider not allowed without --allow-stub-code-agent. "
                "Set OPENAI_API_KEY (or LLM_BASE_URL) for real execution, "
                "or pass --allow-stub-code-agent for testing."
            )
        return
    missing = []
    if not config.base_url:
        missing.append("--base-url (or LLM_BASE_URL env)")
    if provider != "local-openai-compatible" and not config.model:
        missing.append("--model")
    requires_api_key = provider not in {"local-openai-compatible"}
    if requires_api_key and not os.getenv(config.api_key_env):
        key_hint = (
            f"{config.api_key_env} env var "
            f"(or --api-key-env to set a different variable)"
        )
        missing.append(key_hint)
    if missing:
        raise ValueError(
            f"Provider '{provider}' requires: {', '.join(missing)}. "
            f"Pass --allow-stub-code-agent to run in stub (simulation) mode."
        )

async def run_code_command(args):
    from .config import get_config
    from .legacy_runner import run_harness
    from .reporter import Reporter

    cli_overrides = build_config_overrides(args)
    config = get_config(cli_overrides)
    provider = _resolve_code_agent(args)
    _validate_provider_settings(provider, config, getattr(args, "allow_stub_code_agent", False))

    result = await run_harness(
        task=args.task,
        workspace_path=getattr(args, "workspace", None),
        allow_stub=getattr(args, "allow_stub_code_agent", False),
        progress_callback=_print_progress_event,
        config=config,
        image_path=getattr(args, "image", None),
        audio_path=getattr(args, "audio", None),
        video_path=getattr(args, "video", None),
        allow_test_short_circuit=getattr(args, "allow_test_short_circuit", False),
        resume_run_id=getattr(args, "resume", None),
    )

    reporter_git_tools = None
    workspace_path = getattr(args, "workspace", None)
    if workspace_path:
        from .policy import PolicyEngine
        from .tools.git import GitTools
        from .workspace import Workspace
        ws = Workspace(base_path=workspace_path)
        ws.path = os.path.abspath(workspace_path)
        reporter_git_tools = GitTools(workspace=ws, policy_engine=PolicyEngine())

    reporter = Reporter(output_dir=config.report_output_path, git_tools=reporter_git_tools)
    filename = reporter.generate_summary(
        result,
        trace=result.trace or result.events,
        policy_info={"provider": provider},
    )
    if config.report_format == "markdown":
        markdown = reporter.generate_markdown_report(
            result,
            blocked_actions=[
                event["message"] for event in result.events if event["event"] == "policy.blocked"
            ],
            provider=provider,
        )
        md_path = os.path.join(reporter.output_dir, filename.replace(".json", ".md"))
        with open(md_path, "w") as f:
            f.write(markdown)
        print(f"Report saved to {os.path.join(reporter.output_dir, filename)} and {md_path}")
    else:
        print(f"Report saved to {os.path.join(reporter.output_dir, filename)}")

    if not result.success:
        print(f"ERROR: {result.error}")
        sys.exit(1)
    print(f"SUCCESS: {result.message}")

async def run_code_batch_command(args):
    from .config import get_config
    from .legacy_runner import run_harness
    from .reporter import Reporter

    if not os.path.exists(args.file):
        print(f"ERROR: File not found: {args.file}")
        sys.exit(1)

    with open(args.file) as f:
        scenarios = json.load(f)

    if not isinstance(scenarios, list):
        print("ERROR: scenarios.json must be a list of objects.")
        sys.exit(1)

    cli_overrides = build_config_overrides(args)
    config = get_config(cli_overrides)

    concurrency = min(max(1, getattr(args, "concurrency", 1)), 4)
    semaphore = asyncio.Semaphore(concurrency)

    print(f"Starting batch of {len(scenarios)} scenarios (Concurrency: {concurrency})")

    async def wrapped_run(scenario):
        async with semaphore:
            name = scenario.get("name", "unnamed")
            task = scenario.get("task")
            agent_id = scenario.get("agent_id") or config.code_agent

            # Detect provider for this task
            provider = _resolve_code_agent(args)
            _validate_provider_settings(
                provider, config, getattr(args, "allow_stub_code_agent", False)
            )

            print(f"  [START] {name}")
            # Pass workspace=None so run_harness creates an isolated temporary workspace.
            result = await run_harness(
                task=task,
                allow_stub=getattr(args, "allow_stub_code_agent", False),
                progress_callback=_print_progress_event,
                config=config.model_copy(
                    update={
                        "code_agent": agent_id,
                        "provider": provider,
                        "loop_timeout": scenario.get("timeout", config.loop_timeout),
                    }
                ),
                allow_test_short_circuit=getattr(args, "allow_test_short_circuit", False),
            )
            print(f"  [{'DONE' if result.success else 'FAIL'}] {name}")
            return {"name": name, "success": result.success, "result": result.model_dump()}

    tasks = [wrapped_run(s) for s in scenarios]
    results = await asyncio.gather(*tasks)

    # Report final summary
    success_count = sum(1 for r in results if r["success"])
    print(f"\nBatch Summary: {success_count}/{len(results)} successful")

    # Save aggregated reports
    timestamp = int(time.time())
    report_base = os.path.join(config.report_output_path, f"batch_report_{timestamp}")
    os.makedirs(config.report_output_path, exist_ok=True)

    # JSON
    with open(f"{report_base}.json", "w") as f:
        json.dump(results, f, indent=2)

    # Markdown
    reporter = Reporter(output_dir=config.report_output_path)
    batch_md = reporter.generate_batch_markdown_report(results)
    with open(f"{report_base}.md", "w") as f:
        f.write(batch_md)

    print(f"Reports saved to {report_base}.json and .md")

    if success_count < len(results):
        sys.exit(1)

async def run_health_command(args):
    results = await HealthCheck.check_local_env()
    print(f"Harness Health: {results['status']}")
    for check, val in results["checks"].items():
        print(f"  {check}: {'OK' if val else 'FAILED'}")

    if not getattr(args, "local_only", False):
        from .config import get_config

        config = get_config(
            {
                "config": getattr(args, "config", None),
                "provider": _resolve_code_agent(args),
                "base_url": getattr(args, "base_url", None),
                "model": getattr(args, "model", None),
                "api_key_env": getattr(args, "api_key_env", None),
                "timeout": getattr(args, "timeout", None),
                "local_model_timeout": getattr(args, "local_model_timeout", None),
                "auto_increase_timeout": getattr(args, "auto_increase_timeout", None),
                "max_retries": getattr(args, "max_retries", None),
                "stream": getattr(args, "stream", None),
                "stream_local_default": getattr(args, "stream_local_default", None),
                "verbose_stream": getattr(args, "verbose_stream", None),
                "tool_calling": getattr(args, "tool_calling", None),
                "supports_tool_calling": getattr(args, "supports_tool_calling", None),
            }
        )
        provider = _resolve_code_agent(args)
        _validate_provider_settings(provider, config, allow_stub=(provider == "stub"))
        from .agent_client import AgentClient
        client = AgentClient(
            agent_id=config.code_agent,
            base_url=config.base_url,
            provider=config.provider,
            model=config.model,
            api_key_env=config.api_key_env,
            timeout=config.timeout,
            max_retries=config.max_retries,
            local_model_timeout=config.local_model_timeout,
            auto_increase_timeout=config.auto_increase_timeout,
            stream=config.stream,
            stream_local_default=config.stream_local_default,
            verbose_stream=config.verbose_stream,
            tool_calling=config.tool_calling,
            supports_tool_calling=config.supports_tool_calling,
        )
        remote = await HealthCheck.check_provider(client)
        print(f"Remote Health: {remote['status']}")
        for key, value in remote.items():
            if key != "status":
                print(f"  {key}: {Sanitizer.sanitize_text(value)}")

def run_security_command(check_only: bool):
    from .policy import PolicyEngine

    policy = PolicyEngine()
    secret_sample = "Authorization: Bearer token-123 api_key=sk-secret"
    redacted = Sanitizer.sanitize_text(secret_sample)
    checks = {
        "shell_policy_blocks_dangerous": not policy.evaluate_shell_command("rm -rf /").allowed,
        "file_policy_blocks_secret_files": not policy.evaluate_file_path(".env").allowed,
        "sanitizer_redacts_secrets": "token-123" not in redacted and "sk-secret" not in redacted,
    }
    status = "healthy" if all(checks.values()) else "unhealthy"
    print(f"Security Audit: {status}")
    for check, ok in checks.items():
        print(f"  {check}: {'OK' if ok else 'FAILED'}")
    if not check_only and not all(checks.values()):
        sys.exit(1)

async def run_eval_command(args):
    from .evals import EvalRunner
    from .evals.loader import EvalLoader, EvalLoadError
    from .evals.report import EvalReportGenerator

    if not os.path.exists(args.suite):
        print(f"ERROR: Suite file not found: {args.suite}")
        sys.exit(1)

    try:
        suite = EvalLoader.load(args.suite)
    except EvalLoadError as exc:
        print(f"ERROR: Failed to load eval suite: {exc}")
        sys.exit(1)

    provider = getattr(args, "code_agent", None) or "stub"
    allow_stub = getattr(args, "allow_stub_code_agent", True)

    runner = EvalRunner(
        suite=suite,
        provider=provider,
        model=getattr(args, "model", None) or "",
        base_url=getattr(args, "base_url", None) or "",
        api_key_env=getattr(args, "api_key_env", None) or "OPENAI_API_KEY",
        allow_stub=allow_stub,
        sandbox=getattr(args, "sandbox", False),
        docker_image=getattr(args, "docker_image", None) or "python:3.12-slim",
        self_heal=getattr(args, "self_heal", True),
        max_steps=getattr(args, "max_steps", 10),
        request_timeout=getattr(args, "timeout", 30.0),
        max_retries=getattr(args, "max_retries", 3),
        temp_base_dir=getattr(args, "temp_base_dir", None),
        max_output_chars=10000,
        report_output_path=getattr(args, "output", "artifacts/llm_harness"),
        judge_provider=getattr(args, "judge", "disabled"),
        judge_model=getattr(args, "judge_model", None) or "",
        judge_base_url=getattr(args, "judge_base_url", None) or "",
        judge_api_key_env=getattr(args, "judge_api_key_env", None) or "OPENAI_API_KEY",
        judge_threshold=float(getattr(args, "judge_threshold", 0.75)),
        track=bool(getattr(args, "track", False)),
        track_dir=getattr(args, "track_dir", "artifacts/evals/runs"),
        prompt_version=getattr(args, "prompt_version", ""),
        prompt_hash=getattr(args, "prompt_hash", ""),
        policy_preset=getattr(args, "policy_preset", ""),
        suite_path=getattr(args, "suite", ""),
        pricing_file=getattr(args, "pricing_file", None),
        max_cost_per_run=getattr(args, "max_cost_per_run", None),
        max_tokens_per_run=getattr(args, "max_tokens_per_run", None),
        experiment_tracker=getattr(args, "experiment_tracker", "local"),
        mlflow_tracking_uri=getattr(args, "mlflow_tracking_uri", None),
        mlflow_experiment=getattr(args, "mlflow_experiment", None),
    )

    concurrency = min(max(1, getattr(args, "concurrency", 1)), 4)
    result = await runner.run_all(concurrency=concurrency)

    output_dir = getattr(args, "output", "artifacts/llm_harness")
    os.makedirs(output_dir, exist_ok=True)

    json_path = None
    md_path = None

    report_format = getattr(args, "report", "json")
    if report_format in ("json", "both"):
        json_path = EvalReportGenerator.save_json_report(result, output_dir)

    if report_format in ("markdown", "both"):
        md_path = EvalReportGenerator.save_markdown_report(result, output_dir)

    judge_scores = [
        cs.judge_verdict.score
        for cs in result.case_scores
        if cs.judge_verdict is not None
    ]
    judge_avg = sum(judge_scores) / len(judge_scores) if judge_scores else None

    accuracy_pct = f"{result.accuracy * 100:.1f}%"
    print(f"\nEval Suite '{result.suite_name}' Complete:")
    print(f"  Passed: {result.passed}/{result.total_cases} ({accuracy_pct})")
    print(f"  pass@1: {result.pass_at_1:.4f}")
    print(f"  Duration: {result.total_duration_seconds:.2f}s")
    if judge_avg is not None:
        print(f"  Judge Avg Score: {judge_avg:.4f}")
    if json_path:
        print(f"  JSON report: {json_path}")
    if md_path:
        print(f"  Markdown report: {md_path}")

    if result.failed > 0:
        sys.exit(1)


def run_server_command(args):
    import uvicorn

    from .server.app import server_config
    server_config.api_key_env = getattr(args, "api_key_env", None)
    server_config.allow_stub = bool(getattr(args, "allow_stub_code_agent", False))
    print(f"Starting LLM Harness API Server on {args.host}:{args.port}...")
    uvicorn.run(
        "scripts.llm_harness.server.app:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )


def run_plugins_command(args):
    from .plugins import plugin_registry
    if args.plugin_command == "list":
        print(
            f"Loaded Plugins (Enabled={getattr(args, 'enable_plugins', False)}):"
        )
        if not plugin_registry.plugins:
            print("  No plugins loaded.")
        for name, plugin in plugin_registry.plugins.items():
            print(
                f"  - {name} (Version: {plugin.metadata.version}, "
                f"Source: {plugin.metadata.source})"
            )
            print(f"    Description: {plugin.metadata.description}")
            
    elif args.plugin_command == "validate":
        print("Validating plugin registry...")
        print(f"  Plugins count: {len(plugin_registry.plugins)}")
        print(f"  Providers registered: {list(plugin_registry.providers.keys())}")
        print(f"  Tools registered: {list(plugin_registry.tools.keys())}")
        print(f"  Scorers registered: {list(plugin_registry.scorers.keys())}")
        print(f"  Policy Rules registered: {list(plugin_registry.policy_rules.keys())}")
        # Basic validation checks
        for name, tool in plugin_registry.tools.items():
            if not callable(tool):
                print(f"ERROR: Tool '{name}' is not callable")
                sys.exit(1)
        for name, scorer in plugin_registry.scorers.items():
            if not callable(scorer):
                print(f"ERROR: Scorer '{name}' is not callable")
                sys.exit(1)
        print("Registry Validation: OK")


async def run_benchmark_command(args):
    from .benchmarks import BenchmarkSuiteRunner, compare_benchmarks
    suite_type = getattr(args, "suite_type", "coding")
    if args.benchmark_command == "run":
        provider = _resolve_code_agent(args)

        if suite_type == "gsm8k":
            from .benchmarks.gsm8k import GSM8KAdapter
            _runner: Any = GSM8KAdapter(
                suite_path=args.suite,
                provider=provider,
                model=getattr(args, "model", "") or "",
                allow_stub=getattr(args, "allow_stub_code_agent", False)
            )
        elif suite_type == "swebench":
            from .benchmarks.swebench_adapter import SWEBenchAdapter
            _runner = SWEBenchAdapter(
                suite_path=args.suite,
                provider=provider,
                model=getattr(args, "model", "") or "",
                allow_stub=getattr(args, "allow_stub_code_agent", False)
            )
        else:
            _runner = BenchmarkSuiteRunner(
                suite_path=args.suite,
                provider=provider,
                model=getattr(args, "model", "") or "",
                allow_stub=getattr(args, "allow_stub_code_agent", False)
            )
        runner = _runner
        print(f"Running {suite_type} benchmark suite from {args.suite}...")
        summary = await runner.run()
        
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)
            
        print("\nBenchmark Suite Run Complete:")
        print(f"  Suite: {summary['suite']}")
        print(f"  Total Tasks: {summary['total_tasks']}")
        print(f"  Solved: {summary['solved']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Accuracy: {summary['accuracy'] * 100:.1f}%")
        print(f"  pass@1: {summary['pass_at_1']:.4f}")
        print(f"  Duration: {summary['duration_ms'] / 1000:.2f}s")
        print(f"  Tokens: {summary['tokens']}")
        print(f"  Estimated Cost: {summary['estimated_cost']:.4f}")
        print(f"  Saved detailed result to: {args.output}")

    elif args.benchmark_command == "compare":
        print(f"Comparing result {args.result} with baseline {args.baseline}...")
        if not os.path.exists(args.result):
            print(f"ERROR: Result file not found: {args.result}")
            sys.exit(1)
        with open(args.result, "r") as f:
            current_summary = json.load(f)
            
        try:
            comparison = compare_benchmarks(
                current_summary=current_summary,
                baseline_path=args.baseline,
                threshold=args.threshold
            )
            print("\nBenchmark Comparison Result:")
            print(f"  Current Accuracy: {comparison['current_accuracy'] * 100:.1f}%")
            print(f"  Baseline Accuracy: {comparison['baseline_accuracy'] * 100:.1f}%")
            print(f"  Difference: {comparison['diff'] * 100:+.1f}%")
            print(f"  Status: {comparison['status'].upper()}")
            
            if comparison["regressed"]:
                print(f"ERROR: Regression detected above threshold ({args.threshold * 100:.1f}%)")
                sys.exit(1)
            else:
                print("No significant regression detected.")
        except Exception as e:
            print(f"ERROR comparing benchmarks: {e}")
            sys.exit(1)
