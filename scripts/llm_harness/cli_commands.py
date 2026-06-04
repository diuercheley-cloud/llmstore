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
        "allow_native_tools_for_local": getattr(args, "allow_native_tools_for_local", None),
        "lm_studio_compatibility": getattr(args, "lm_studio_compatibility", None),
        "capability_cache_ttl_seconds": getattr(args, "capability_cache_ttl_seconds", None),
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
        "auto": getattr(args, "auto", None),
        "max_auto_fixes": getattr(args, "max_auto_fixes", None),
        "stop_on_risk": getattr(args, "stop_on_risk", None),
        "require_approval_for_edits": getattr(args, "require_approval_for_edits", None),
        "model_profile": getattr(args, "model_profile", None),
        "fallback_model_profile": getattr(args, "fallback_model_profile", None),
        "allow_cloud_models": getattr(args, "allow_cloud_models", None),
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
        "allow_native_tools_for_local": getattr(args, "allow_native_tools_for_local", None),
        "lm_studio_compatibility": getattr(args, "lm_studio_compatibility", None),
        "capability_cache_ttl_seconds": getattr(args, "capability_cache_ttl_seconds", None),
        "multimodal": getattr(args, "multimodal", None),
        "max_tokens": getattr(args, "max_tokens", None),
        "model_profile": getattr(args, "model_profile", None),
        "fallback_model_profile": getattr(args, "fallback_model_profile", None),
        "allow_cloud_models": getattr(args, "allow_cloud_models", None),
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


def _resolve_execution_target(config, args, task_type: str | None = None):
    from .model_router import ModelRouter

    router = ModelRouter(config)
    profile_name = getattr(args, "model_profile", None) or getattr(config, "model_profile", None)
    fallback_profile_name = (
        getattr(args, "fallback_model_profile", None)
        or getattr(config, "fallback_model_profile", None)
    )

    if profile_name:
        profile_cfg = router.resolve_profile(profile_name)
        if not profile_cfg:
            raise ValueError(f"Model profile '{profile_name}' not found in configuration.")
    elif task_type:
        resolved_profile_name, profile_cfg = router.resolve_by_task_type(task_type)
        if resolved_profile_name == "default-config":
            profile_name = None
            profile_cfg = None
        else:
            profile_name = resolved_profile_name
    else:
        profile_cfg = None

    if not profile_cfg:
        provider_name = _resolve_code_agent(args)
        return provider_name, config, None, fallback_profile_name

    if not router.check_policy(profile_cfg):
        raise PermissionError(
            f"Cloud model provider '{profile_cfg.get('provider')}' is blocked by policy."
        )

    config_updates = {
        "provider": profile_cfg.get("provider", getattr(config, "provider", "")),
        "model": profile_cfg.get("model", getattr(config, "model", "")),
        "base_url": profile_cfg.get("base_url", getattr(config, "base_url", "")),
        "api_key_env": profile_cfg.get(
            "api_key_env",
            getattr(config, "api_key_env", "OPENAI_API_KEY"),
        ),
        "timeout": profile_cfg.get("timeout", getattr(config, "timeout", 30.0)),
        "model_profile": profile_name,
        "fallback_model_profile": fallback_profile_name,
    }
    resolved_config = config.model_copy(update=config_updates)
    provider_name = profile_cfg.get("provider", _resolve_code_agent(args))
    return provider_name, resolved_config, profile_name, fallback_profile_name

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
                "allow_native_tools_for_local": getattr(args, "allow_native_tools_for_local", None),
                "capability_cache_ttl_seconds": getattr(args, "capability_cache_ttl_seconds", None),
            }
        )
        provider = _resolve_code_agent(args)
        _validate_provider_settings(provider, config, allow_stub=(provider == "stub"))
        from .agent_client import AgentClient
        from .cache import LocalCache
        cache = LocalCache(mode=config.cache, cache_dir=config.cache_dir)
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
            allow_native_tools_for_local=config.allow_native_tools_for_local,
            lm_studio_compatibility=config.lm_studio_compatibility,
            capability_cache_ttl_seconds=config.capability_cache_ttl_seconds,
            cache=cache,
            max_tokens=config.max_tokens,
        )
        remote = await HealthCheck.check_provider(client)
        print(f"Remote Health: {remote['status']}")
        for key, value in remote.items():
            if key != "status":
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for sub_key, sub_value in value.items():
                        print(f"    {sub_key}: {Sanitizer.sanitize_text(str(sub_value))}")
                else:
                    print(f"  {key}: {Sanitizer.sanitize_text(str(value))}")

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
    from .config import get_config
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

    config = get_config(build_config_overrides(args))
    provider = getattr(args, "code_agent", None) or "stub"
    allow_stub = getattr(args, "allow_stub_code_agent", True)

    runner = EvalRunner(
        suite=suite,
        provider=provider,
        model=config.model,
        base_url=config.base_url,
        api_key_env=config.api_key_env,
        allow_stub=allow_stub,
        sandbox=config.sandbox,
        docker_image=config.docker_image,
        self_heal=config.self_heal,
        max_steps=config.max_steps,
        request_timeout=config.timeout,
        max_retries=config.max_retries,
        temp_base_dir=config.temp_base_dir,
        max_output_chars=config.max_output_chars,
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
        pricing_file=config.pricing_file,
        max_cost_per_run=config.max_cost_per_run,
        max_tokens_per_run=config.max_tokens_per_run,
        model_max_tokens=config.max_tokens,
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

        base_url = getattr(args, "base_url", None) or ""
        if suite_type == "gsm8k":
            from .benchmarks.gsm8k import GSM8KAdapter
            _runner: Any = GSM8KAdapter(
                suite_path=args.suite,
                provider=provider,
                model=getattr(args, "model", "") or "",
                base_url=base_url,
                allow_stub=getattr(args, "allow_stub_code_agent", False)
            )
        elif suite_type == "swebench":
            from .benchmarks.swebench_adapter import SWEBenchAdapter
            _runner = SWEBenchAdapter(
                suite_path=args.suite,
                provider=provider,
                model=getattr(args, "model", "") or "",
                base_url=base_url,
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


async def run_chat_command(args):
    from .config import get_config
    from .context import ContextManager
    from .ide import IDEChatSession, build_context_bundle, parse_refs
    from .ide.rules import load_rules_for_path
    from .indexing import DocsManager
    from .languages import detect_primary_language_in_workspace
    from .memory import LocalMemory
    from .policy import PolicyEngine
    from .prompt_builder import PromptBuilder
    from .providers import create_code_agent
    from .tokenizer import TokenCounter
    from .workspace import Workspace

    # Initialize workspace
    workspace_path = getattr(args, "workspace", None) or "."
    ws = Workspace(base_path=workspace_path)
    
    cli_overrides = build_config_overrides(args)
    config = get_config(cli_overrides)
    provider_name, config, _, _ = _resolve_execution_target(config, args, task_type="chat")
    _validate_provider_settings(
        provider_name, config, getattr(args, "allow_stub_code_agent", False)
    )

    async with ws as workspace:
        policy_engine = PolicyEngine(config=config.model_dump())
        
        # Memory
        memory_dir = getattr(args, "memory_dir", None) or config.memory_dir or ".llm_harness_memory"
        memory = LocalMemory(memory_dir=memory_dir)
        
        # Load rules
        rules_context = load_rules_for_path(None, workspace.path)
        docs_context = DocsManager(
            workspace_root=workspace.path,
            policy_engine=PolicyEngine(config=config.model_dump()),
        ).build_prompt_context()
        language_profile = detect_primary_language_in_workspace(workspace.path)

        prompt_builder = PromptBuilder(
            policy_summary=policy_engine.describe_for_agent(),
            memory_context=memory.get_context_for_prompt(),
            rules_context=rules_context,
            retrieved_context=docs_context,
            language_profile=language_profile,
            interaction_mode="chat",
        )

        tokenizer = TokenCounter(method="auto")
        context_manager = ContextManager(
            max_context_tokens=getattr(args, "token_budget", 4096),
            reserved_output_tokens=1024,
            token_counter=tokenizer
        )

        provider_config = config.model_dump()
        provider_config["plain_chat"] = True
        provider = create_code_agent(provider_name, provider_config)

        session = IDEChatSession(
            provider=provider,
            prompt_builder=prompt_builder,
            policy_engine=policy_engine,
            memory=memory,
            context_manager=context_manager,
            token_budget=getattr(args, "token_budget", 4096),
            rules_context=rules_context
        )

        image_path = getattr(args, "image", None)
        initial_image_sent = False

        if args.message:
            # Single message execution
            refs = parse_refs(args.message, workspace)
            context_budget = max(500, getattr(args, "token_budget", 4096) - 2000)
            context_bundle = await build_context_bundle(
                refs, workspace, policy_engine, token_budget=context_budget
            )
            
            message_content = args.message
            if image_path:
                from .multimodal import validate_and_load_image
                metadata, b64_data = validate_and_load_image(image_path, workspace.path)
                message_content = [
                    {"type": "text", "text": args.message or ""},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{metadata.mime_type};base64,{b64_data}"
                        }
                    }
                ]

            reply = await session.send_message(message_content, context_bundle=context_bundle)
            print(reply)
        else:
            # Interactive chat loop
            print("=== LLM Harness IDE Assistant Chat (type 'exit' or 'quit' to end) ===")
            while True:
                try:
                    user_input = input("\nYou: ").strip()
                except (KeyboardInterrupt, EOFError):
                    print("\nGoodbye!")
                    break
                
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit"):
                    print("Goodbye!")
                    break
                
                refs = parse_refs(user_input, workspace)
                context_budget = max(500, getattr(args, "token_budget", 4096) - 2000)
                context_bundle = await build_context_bundle(
                    refs, workspace, policy_engine, token_budget=context_budget
                )

                message_content = user_input
                if image_path and not initial_image_sent:
                    from .multimodal import validate_and_load_image
                    metadata, b64_data = validate_and_load_image(image_path, workspace.path)
                    message_content = [
                        {"type": "text", "text": user_input},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{metadata.mime_type};base64,{b64_data}"
                            }
                        }
                    ]
                    initial_image_sent = True

                reply = await session.send_message(message_content, context_bundle=context_bundle)
                print(f"\nAssistant: {reply}")


async def run_edit_inline_command(args):
    from .config import get_config
    from .ide import InlineEditRequest, build_context_bundle, parse_refs, perform_inline_edit
    from .policy import PolicyEngine
    from .providers import create_code_agent
    from .workspace import Workspace

    # Parse range
    range_str = args.range
    start_line, end_line = 1, 1
    if ":" in range_str:
        parts = range_str.split(":")
        start_line = int(parts[0])
        end_line = int(parts[1])
    elif "-" in range_str:
        parts = range_str.split("-")
        start_line = int(parts[0])
        end_line = int(parts[1])
    else:
        start_line = end_line = int(range_str)

    # Initialize workspace
    workspace_path = getattr(args, "workspace", None) or "."
    ws = Workspace(base_path=workspace_path)

    cli_overrides = build_config_overrides(args)
    config = get_config(cli_overrides)
    provider_name, config, _, _ = _resolve_execution_target(
        config, args, task_type="inline-edit"
    )
    _validate_provider_settings(
        provider_name, config, getattr(args, "allow_stub_code_agent", False)
    )

    async with ws as workspace:
        policy_engine = PolicyEngine(config=config.model_dump())
        provider_config = config.model_dump()
        provider_config["plain_chat"] = True
        provider = create_code_agent(provider_name, provider_config)

        # Collect context references
        context_strs = args.context
        context_refs_list = []
        for ctx_str in context_strs:
            if not ctx_str.startswith("@"):
                ctx_str = "@" + ctx_str
            context_refs_list.extend(parse_refs(ctx_str, workspace))
        
        # Build context bundle
        context_bundle = await build_context_bundle(
            context_refs_list, workspace, policy_engine, token_budget=4000
        )

        # Create InlineEditRequest
        request = InlineEditRequest(
            file_path=args.file_path,
            start_line=start_line,
            end_line=end_line,
            instruction=args.instruction,
            context_refs=context_refs_list
        )

        res = await perform_inline_edit(
            request=request,
            provider=provider,
            policy_engine=policy_engine,
            workspace=workspace,
            dry_run=args.dry_run,
            context_bundle=context_bundle
        )

        if res["success"]:
            if args.dry_run:
                print("--- Dry-Run Diff Preview ---")
                print(res["diff"])
                print("----------------------------")
                print("SUCCESS: Dry-run check completed successfully (no files changed).")
            else:
                print("SUCCESS: Inline edit applied successfully.")
        else:
            patch_res = res.get("patch_result")
            err_msg = patch_res.error if patch_res else "Unknown error"
            print(f"ERROR: Inline edit failed: {err_msg}")
            sys.exit(1)


def run_index_command(args):
    import sys

    from .indexing import RepositoryIndexer, query_index

    workspace_path = getattr(args, "workspace", None) or "."
    
    if args.index_command == "build":
        indexer = RepositoryIndexer(workspace_root=workspace_path)
        print(f"Building repository index for workspace '{workspace_path}'...")
        indexed = indexer.build_index()
        print(f"SUCCESS: Indexed {len(indexed)} files.")
    elif args.index_command == "query":
        query_str = args.query
        print(f"Querying index for '{query_str}'...")
        results = query_index(query_str, workspace_root=workspace_path)
        if not results:
            print("No matching files or symbols found.")
        else:
            print(f"Found {len(results)} matches:")
            for res in results[:10]:
                print(f"  [{res['language'].upper()}] {res['path']} (Score: {res['score']})")
                if res['symbols']:
                    print(f"    Symbols: {', '.join(res['symbols'])}")
    else:
        print("ERROR: Unknown index command.")
        sys.exit(1)


def run_docs_command(args):
    import sys

    from .indexing import DocsManager
    from .policy import PolicyEngine

    workspace_path = getattr(args, "workspace", None) or "."
    policy_engine = PolicyEngine(config=build_config_overrides(args))
    docs_mgr = DocsManager(workspace_root=workspace_path, policy_engine=policy_engine)

    if args.docs_command == "add":
        print(f"Adding documentation config: name={args.name}, url={args.url}")
        docs_mgr.add_doc(
            name=args.name,
            url=args.url,
            allowlist_domain=getattr(args, "allowlist_domain", None)
        )
        print("SUCCESS: Config updated.")
    elif args.docs_command == "refresh":
        print("Refreshing external docs cache...")
        docs_mgr.refresh_docs()
        print("SUCCESS: Refresh completed.")
    else:
        print("ERROR: Unknown docs command.")
        sys.exit(1)


async def run_fix_error_command(args):
    import os
    import sys
    from unittest.mock import patch

    from .config import get_config
    from .diagnostics import diagnose_errors
    from .legacy_runner import run_harness

    workspace_path = getattr(args, "workspace", None) or "."
    error_content = ""

    if getattr(args, "from_file", None):
        log_path = args.from_file
        if not os.path.exists(log_path):
            print(f"ERROR: File '{log_path}' not found.")
            sys.exit(1)
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            error_content = f.read()
    elif getattr(args, "run_command", None):
        cmd = args.run_command
        print(f"Executing command: '{cmd}'...")
        from .policy import PolicyEngine
        policy = PolicyEngine(config=build_config_overrides(args))
        decision = policy.evaluate_shell_command(cmd)
        if not decision.allowed:
            print(f"ERROR: Command execution blocked by policy: {decision.reason}")
            sys.exit(1)

        import subprocess
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        error_content = proc.stdout + "\n" + proc.stderr
        print(f"Command finished with exit code {proc.returncode}.")
    else:
        print("ERROR: Either --from-file or --command must be specified.")
        sys.exit(1)

    diagnostics = diagnose_errors(error_content)
    if diagnostics:
        print(f"Diagnosed {len(diagnostics)} issues:")
        for d in diagnostics[:5]:
            print(f"  [{d.severity.upper()}] File: {d.file}, Line: {d.line}")
            print(f"    Message: {d.message}")
            print(f"    Suggested Action: {d.suggested_action}")
    else:
        print("No specific diagnostics identified. Passing raw log to agent.")

    task = "Fix the following execution/test errors.\n\n"
    if diagnostics:
        task += "Diagnosed Issues:\n"
        for d in diagnostics:
            task += (
                f"- File: {d.file}, Line: {d.line}\n"
                f"  Message: {d.message}\n"
                f"  Suggested Action: {d.suggested_action}\n"
            )
    task += f"\nRaw Error Logs:\n{error_content}\n"

    cli_overrides = build_config_overrides(args)
    config = get_config(cli_overrides)
    provider = _resolve_code_agent(args)
    _validate_provider_settings(provider, config, getattr(args, "allow_stub_code_agent", False))

    if getattr(args, "dry_run", False):
        print("[DRY-RUN] Dry run mode active. Disabling actual file writes and patch applications.")
        from .coding_loop import CodingLoop

        orig_apply = CodingLoop.apply_patch
        async def dry_apply_patch(self, diff_content: str, dry_run: bool = False):
            print(f"[DRY-RUN] Proposed Patch:\n{diff_content}")
            return await orig_apply(self, diff_content, dry_run=True)

        async def dry_write_file(self, path: str, content: str):
            print(f"[DRY-RUN] Write file to {path}:\n{content}")
            return {"success": True, "message": "Dry-run write simulated."}

        async def dry_replace_content(self, path: str, old_content: str, new_content: str):
            print(f"[DRY-RUN] Replace content in {path}:\n{old_content} -> {new_content}")
            return {"success": True, "message": "Dry-run replacement simulated."}

        with patch.object(CodingLoop, "apply_patch", dry_apply_patch), \
             patch.object(CodingLoop, "write_file", dry_write_file), \
             patch.object(CodingLoop, "replace_content", dry_replace_content):
            result = await run_harness(
                task=task,
                workspace_path=workspace_path,
                allow_stub=getattr(args, "allow_stub_code_agent", False),
                progress_callback=_print_progress_event,
                config=config,
                allow_test_short_circuit=getattr(args, "allow_test_short_circuit", False),
            )
    else:
        result = await run_harness(
            task=task,
            workspace_path=workspace_path,
            allow_stub=getattr(args, "allow_stub_code_agent", False),
            progress_callback=_print_progress_event,
            config=config,
            allow_test_short_circuit=getattr(args, "allow_test_short_circuit", False),
        )

    if result.success:
        print("SUCCESS: Error correction completed successfully.")
    else:
        print(f"FAILURE: Error correction failed: {result.error}")


async def run_terminal_command(args):
    import os
    import re
    import sys

    from .diagnostics import diagnose_errors
    from .policy import PolicyEngine


    policy_engine = PolicyEngine(config=build_config_overrides(args))

    if args.terminal_command == "diagnose":
        if getattr(args, "stderr_file", None):
            stderr_file = args.stderr_file
            if not os.path.exists(stderr_file):
                print(f"ERROR: Stderr log file '{stderr_file}' not found.")
                sys.exit(1)
            with open(stderr_file, "r", encoding="utf-8", errors="ignore") as f:
                error_content = f.read()
        elif getattr(args, "last_command", None):
            cmd = args.last_command
            decision = policy_engine.evaluate_shell_command(cmd)
            if not decision.allowed:
                print(f"ERROR: Command execution blocked by policy: {decision.reason}")
                sys.exit(1)

            import subprocess
            print(f"Executing command: '{cmd}'...")
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            error_content = proc.stdout + "\n" + proc.stderr
        else:
            print("ERROR: Provide either --last-command or --stderr-file.")
            sys.exit(1)

        diagnostics = diagnose_errors(error_content)
        if not diagnostics:
            print("No diagnostics found.")
        else:
            print(f"Diagnosed {len(diagnostics)} issues:")
            for d in diagnostics:
                print(
                    f"- [{d.severity.upper()}] File: {d.file}, "
                    f"Line: {d.line}\n  Message: {d.message}\n"
                )

    elif args.terminal_command == "suggest":
        stderr_file = args.stderr_file
        if not os.path.exists(stderr_file):
            print(f"ERROR: Stderr log file '{stderr_file}' not found.")
            sys.exit(1)
        with open(stderr_file, "r", encoding="utf-8", errors="ignore") as f:
            error_content = f.read()

        diagnostics = diagnose_errors(error_content)
        if not diagnostics:
            print("No diagnostics found in stderr log file.")
            sys.exit(0)

        from .config import get_config
        from .providers import create_code_agent

        config = get_config(build_config_overrides(args))
        provider_name = _resolve_code_agent(args)

        agent = create_code_agent(provider_name, config.model_dump())

        prompt = (
            "Based on the following error diagnostics, suggest a command to fix it. "
            "Respond ONLY with the single suggested command line, nothing else. "
            "Do not include explanation, code blocks, or formatting.\n\n"
            "Diagnostics:\n"
        )
        for d in diagnostics[:3]:
            prompt += f"- File: {d.file}, Line: {d.line}, Error: {d.message}\n"
        prompt += f"\nRaw log excerpt:\n{error_content[:1000]}"

        response = await agent.chat_completion([{"role": "user", "content": prompt}])
        suggestion = response["choices"][0]["message"]["content"].strip()
        suggestion = re.sub(r"^```[a-zA-Z]*\n|```$", "", suggestion).strip()

        print(f"Suggested Command: {suggestion}")

        eval_decision = policy_engine.evaluate_shell_command(suggestion)
        if not eval_decision.allowed:
            print(
                "WARNING: The suggested command was BLOCKED by policy rules: "
                f"{eval_decision.reason}"
            )
        else:
            print("The suggested command is ALLOWED by policy rules.")
    else:
        print("ERROR: Unknown terminal command.")
        sys.exit(1)


def run_multimodal_command(args):
    import sys
    
    if args.multimodal_command == "inspect":
        workspace_path = getattr(args, "workspace", None) or "."
        image_path = args.image_path
        
        from .multimodal import validate_and_load_image
        try:
            metadata, _ = validate_and_load_image(image_path, workspace_path)
            print("Image Inspection Results:")
            print(f"  Filename:   {metadata.filename}")
            print(f"  Mime Type:  {metadata.mime_type}")
            print(f"  Size:       {metadata.size_bytes} bytes")
            print(f"  SHA-256:    {metadata.sha256}")
            if metadata.dimensions:
                print(f"  Dimensions: {metadata.dimensions[0]}x{metadata.dimensions[1]}")
            else:
                print("  Dimensions: Not available (Pillow not installed or failed to read)")
        except Exception as e:
            print(f"ERROR inspecting image: {e}")
            sys.exit(1)
    else:
        print("ERROR: Unknown multimodal command.")
        sys.exit(1)


async def run_complete_command(args):
    from .completions import CompletionRequest, get_completion_suggestions
    from .config import get_config
    
    workspace_path = getattr(args, "workspace", None) or "."
    
    request = CompletionRequest(
        file_path=args.file_path,
        cursor_line=args.line,
        cursor_column=args.column,
    )
    
    cli_overrides = build_config_overrides(args)
    config = get_config(cli_overrides)
    provider_name, config, _, _ = _resolve_execution_target(
        config, args, task_type="completion"
    )
    
    if provider_name not in ("fake", "stub"):
        _validate_provider_settings(
            provider_name, config, getattr(args, "allow_stub_code_agent", False)
        )
        
    completion_config = config.model_dump()
    completion_config["plain_chat"] = True

    suggestions = await get_completion_suggestions(
        request=request,
        workspace_root=workspace_path,
        provider_name=provider_name,
        config_overrides=completion_config,
    )
    
    print("Completion Suggestions:")
    for i, sug in enumerate(suggestions):
        print(f"Suggestion {i+1}:")
        print(f"  Code:       {sug.text}")
        if sug.confidence is not None:
            print(f"  Confidence: {sug.confidence:.2f}")
        if sug.explanation:
            print(f"  Reason:     {sug.explanation}")


def run_ide_command(args):
    import sys

    from .ide.importers import get_ide_config, import_vscode_config
    workspace_path = getattr(args, "workspace", None) or "."

    if args.ide_command == "import-vscode":
        res = import_vscode_config(args.path, workspace_root=workspace_path)
        print("Successfully imported VS Code configuration.")
        settings_count = len(res.get("settings", {}))
        kb_count = len(res.get("keybindings", []))
        ext_count = len(res.get("extensions", []))
        has_rules = res.get("cursor_rules") is not None
        print(f"  Settings keys: {settings_count}")
        print(f"  Keybindings:   {kb_count}")
        print(f"  Extensions:    {ext_count}")
        print(f"  Cursor Rules:  {'Yes' if has_rules else 'No'}")

    elif args.ide_command == "show-config":
        cfg = get_ide_config(workspace_root=workspace_path)
        if not cfg:
            print("No imported configuration found.")
            return
        import json
        print(json.dumps(cfg, indent=2))

    else:
        print("ERROR: Unknown IDE subcommand.")
        sys.exit(1)


async def run_models_command(args):
    import json
    import sys

    from .config import get_config
    from .model_router import ModelRouter, is_cloud_provider
    from .sanitizer import Sanitizer

    cli_overrides = build_config_overrides(args)
    config = get_config(cli_overrides)
    router = ModelRouter(config)

    if args.models_command == "list":
        profiles = router.get_profiles()
        default_profile = router.get_default_profile_name()
        routing = router.models_config.get("routing", {})

        print("Model Profiles:")
        if not profiles:
            print("  No model profiles configured.")
        else:
            for name, profile in profiles.items():
                is_default = " (DEFAULT)" if name == default_profile else ""
                sanitized_profile = Sanitizer.sanitize_data(profile)
                cost = router.estimate_cost(profile)
                is_cloud = "Yes" if is_cloud_provider(profile.get("provider", "")) else "No"
                print(f"  Profile: {name}{is_default}")
                print(f"    Provider:       {sanitized_profile.get('provider')}")
                print(f"    Model:          {sanitized_profile.get('model')}")
                if sanitized_profile.get("base_url"):
                    print(f"    Base URL:       {sanitized_profile.get('base_url')}")
                print(f"    Cloud Model:    {is_cloud}")
                print(
                    f"    Estimated Cost (Input/Output per 1M): "
                    f"{cost.get('prompt_token_price_per_1m')} / "
                    f"{cost.get('completion_token_price_per_1m')} "
                    f"{cost.get('currency')}"
                )
                print()

        if routing:
            print("Routing Configurations:")
            for task_type, p_name in routing.items():
                print(f"  {task_type} -> {p_name}")

    elif args.models_command == "test":
        profile_name = args.profile
        profile_cfg = router.resolve_profile(profile_name)
        if not profile_cfg:
            print(f"ERROR: Model profile '{profile_name}' not found.")
            sys.exit(1)

        sanitized_profile = Sanitizer.sanitize_data(profile_cfg)
        print(f"Testing Model Profile: {profile_name}")
        print(f"  Config: {json.dumps(sanitized_profile, indent=2)}")

        # Check policy
        if not router.check_policy(profile_cfg):
            print("  Policy: BLOCKED (Cloud models are disabled)")
            sys.exit(1)
        else:
            print("  Policy: ALLOWED")

        try:
            from .providers import create_code_agent
            cfg_dict = config.model_dump()
            cfg_dict.update(profile_cfg)
            agent = create_code_agent(profile_cfg.get("provider", "stub"), cfg_dict)
            health = await agent.health_check()
            details = health.get("details", {}) if isinstance(health, dict) else {}
            if details:
                if "selected_model" in details:
                    print(f"  Selected Model: {details.get('selected_model')}")
                if "supports_native_tool_calling" in details:
                    native_support = details.get("supports_native_tool_calling")
                    print(
                        "  Native Tool Calling: "
                        f"{'SUPPORTED' if native_support else 'NOT SUPPORTED'}"
                    )
                probe = details.get("native_tool_calling_probe")
                if probe:
                    print(f"  Native Probe Status: {probe.get('status')}")
                    if probe.get("reason"):
                        print(f"    Reason: {probe.get('reason')}")

            # Try dummy completion
            print("  Sending ping request...")
            messages = [{"role": "user", "content": "ping"}]
            if profile_cfg.get("provider") == "local-openai-compatible":
                cfg_dict["plain_chat"] = True
                agent = create_code_agent(profile_cfg.get("provider", "stub"), cfg_dict)
            res = await agent.chat_completion(messages)
            print("  Response: SUCCESS")
            if res and "choices" in res and res["choices"]:
                content = res["choices"][0].get("message", {}).get("content", "").strip()
                print(f"    Content: {content}")
        except Exception as e:
            print(f"  Response: FAILED - {e}")
            sys.exit(1)


    else:
        print("ERROR: Unknown models subcommand.")
        sys.exit(1)
