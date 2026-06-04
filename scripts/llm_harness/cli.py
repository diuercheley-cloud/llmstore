import argparse
import asyncio
import sys

from ._logging import setup_logging
from .cli_args import (
    add_agent_args,
    add_approval_args,
    add_auto_mode_args,
    add_cache_args,
    add_checkpoint_args,
    add_config_args,
    add_eval_args,
    add_execution_args,
    add_memory_args,
    add_policy_args,
    add_pricing_args,
    add_provider_args,
    add_report_args,
    add_sandbox_args,
    add_tracking_args,
)
from .cli_commands import (
    _resolve_code_agent,  # noqa: F401
    run_autonomous_command,
    run_benchmark_command,
    run_chat_command,
    run_code_batch_command,
    run_code_command,
    run_complete_command,
    run_docs_command,
    run_edit_inline_command,
    run_eval_command,
    run_fix_error_command,
    run_health_command,
    run_ide_command,
    run_index_command,
    run_models_command,
    run_multimodal_command,
    run_plugins_command,
    run_security_command,
    run_server_command,
    run_teams_command,
    run_terminal_command,
)
from .config import HarnessConfig, HarnessConfigError
from .sanitizer import Sanitizer


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="LLM Harness CLI")
    add_config_args(parser)
    add_agent_args(parser)
    parser.add_argument("--enable-plugins", action="store_true", help="Enable dynamic plugins")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Health command
    health_parser = subparsers.add_parser("health", help="Check harness health")
    health_parser.add_argument(
        "--local-only", action="store_true", help="Only check local environment"
    )
    add_provider_args(health_parser)

    # Server command
    server_parser = subparsers.add_parser("server", help="Run LLM Harness API Server")
    server_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    server_parser.add_argument("--port", type=int, default=8765, help="Port to bind to")
    server_parser.add_argument(
        "--api-key-env", default="LLM_HARNESS_SERVER_API_KEY", help="Env var name for auth api key"
    )
    server_parser.add_argument(
        "--allow-stub-code-agent",
        action="store_true",
        help="Explicitly allow stub provider in server mode",
    )

    # Plugins command
    plugins_parser = subparsers.add_parser("plugins", help="Manage plugins")
    plugins_subparsers = plugins_parser.add_subparsers(
        dest="plugin_command", help="Plugin commands"
    )
    plugins_subparsers.add_parser("list", help="List loaded plugins")
    plugins_subparsers.add_parser("validate", help="Validate plugin registry")

    # Benchmark command
    benchmark_parser = subparsers.add_parser("benchmark", help="Run standard benchmarks")
    benchmark_subparsers = benchmark_parser.add_subparsers(
        dest="benchmark_command", help="Benchmark commands"
    )
    run_benchmark_parser = benchmark_subparsers.add_parser(
        "run", help="Run standard benchmark suite"
    )
    run_benchmark_parser.add_argument(
        "--suite", required=True, help="Path to benchmark JSON suite"
    )
    run_benchmark_parser.add_argument(
        "--suite-type",
        choices=["coding", "gsm8k", "swebench"],
        default="coding",
        help="Type of benchmark suite (coding=HumanEval, gsm8k=math, swebench=SWE-bench)",
    )
    run_benchmark_parser.add_argument(
        "--output",
        default="benchmark_result.json",
        help="Path to save result summary JSON",
    )
    add_provider_args(
        run_benchmark_parser, default_code_agent="stub", default_allow_stub=True
    )
    
    compare_benchmark_parser = benchmark_subparsers.add_parser(
        "compare", help="Compare benchmark run with baseline"
    )
    compare_benchmark_parser.add_argument(
        "--result", required=True, help="Path to benchmark result summary JSON"
    )
    compare_benchmark_parser.add_argument(
        "--baseline",
        required=True,
        help="Path to baseline benchmark result JSON",
    )
    compare_benchmark_parser.add_argument(
        "--threshold",
        type=float,
        default=0.05,
        help="Regression fail threshold",
    )

    # Code command
    code_parser = subparsers.add_parser("code", help="Run single coding task")
    code_parser.add_argument("--task", required=True, help="Task description")
    code_parser.add_argument("--agent-id", help="Agent ID")
    code_parser.add_argument("--workspace", help="Custom workspace path")
    code_parser.add_argument("--image", help="Path to image file for multi-modal task")
    code_parser.add_argument("--audio", help="Path to audio file for multi-modal task")
    code_parser.add_argument("--video", help="Path to video file for multi-modal task")
    add_provider_args(code_parser)
    add_sandbox_args(code_parser)
    add_policy_args(code_parser)
    add_report_args(code_parser)
    add_cache_args(code_parser)
    add_execution_args(code_parser)
    add_pricing_args(code_parser)
    add_memory_args(code_parser)
    add_agent_args(code_parser)
    add_approval_args(code_parser)
    add_checkpoint_args(code_parser)
    add_auto_mode_args(code_parser)

    # Code Batch command
    batch_parser = subparsers.add_parser("code-batch", help="Run batch of coding tasks")
    batch_parser.add_argument("--file", required=True, help="Path to scenarios.json")
    batch_parser.add_argument("--concurrency", type=int, default=1, help="Max parallel tasks")
    add_provider_args(batch_parser)
    add_sandbox_args(batch_parser)
    add_policy_args(batch_parser)
    add_report_args(batch_parser)
    add_cache_args(batch_parser)
    add_execution_args(batch_parser)
    add_pricing_args(batch_parser)
    add_memory_args(batch_parser)
    add_agent_args(batch_parser)
    add_approval_args(batch_parser)
    add_checkpoint_args(batch_parser)

    # Security command
    security_parser = subparsers.add_parser("security", help="Run security audit")
    security_parser.add_argument("--check-only", action="store_true", help="Dry run check")

    # Eval command
    eval_parser = subparsers.add_parser("eval", help="Run evaluation suite")
    eval_parser.add_argument(
        "--suite", required=True, help="Path to eval_suite.json"
    )
    eval_parser.add_argument(
        "--concurrency", type=int, default=1, help="Max parallel cases"
    )
    add_provider_args(eval_parser, default_code_agent="stub", default_allow_stub=True)
    add_sandbox_args(eval_parser)
    add_policy_args(eval_parser, default_self_heal=True)
    add_execution_args(eval_parser, default_loop_timeout=300)
    add_eval_args(eval_parser)
    add_pricing_args(eval_parser)
    add_memory_args(eval_parser)
    add_agent_args(eval_parser)
    add_approval_args(eval_parser)
    add_checkpoint_args(eval_parser)
    add_tracking_args(eval_parser)

    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Run integrated chat session")
    chat_parser.add_argument("--message", help="Single message to send directly")
    chat_parser.add_argument("--image", help="Path to image file for multi-modal task")
    chat_parser.add_argument("--workspace", help="Custom workspace path")
    chat_parser.add_argument(
        "--token-budget", type=int, default=4096, help="Token budget for history"
    )
    add_provider_args(chat_parser)
    add_sandbox_args(chat_parser)
    add_policy_args(chat_parser)
    add_memory_args(chat_parser)

    # Edit Inline command
    edit_inline_parser = subparsers.add_parser("edit-inline", help="Run inline code editor")
    edit_inline_parser.add_argument("file_path", help="Target file path")
    edit_inline_parser.add_argument(
        "--range", required=True, help="Line range (e.g. 10:25 or 10-25)"
    )
    edit_inline_parser.add_argument(
        "--instruction", required=True, help="Refactoring/editing instruction"
    )
    edit_inline_parser.add_argument(
        "--context", nargs="*", default=[], help="Context references starting with @"
    )
    edit_inline_parser.add_argument("--workspace", help="Custom workspace path")
    edit_inline_parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate and validate diff without writing to file"
    )
    add_provider_args(edit_inline_parser)
    add_sandbox_args(edit_inline_parser)
    add_policy_args(edit_inline_parser)
    add_memory_args(edit_inline_parser)

    # Index command
    index_parser = subparsers.add_parser("index", help="Repository indexing and querying")
    index_parser.add_argument("--workspace", help="Custom workspace path")
    index_subparsers = index_parser.add_subparsers(
        dest="index_command", help="Index commands"
    )
    index_subparsers.add_parser("build", help="Build repository index")
    query_parser = index_subparsers.add_parser("query", help="Query repository index")
    query_parser.add_argument("query", help="Search query string")

    # Docs command
    docs_parser = subparsers.add_parser("docs", help="External documentation helper")
    docs_parser.add_argument("--workspace", help="Custom workspace path")
    add_policy_args(docs_parser)
    docs_subparsers = docs_parser.add_subparsers(
        dest="docs_command", help="Docs commands"
    )
    doc_add_parser = docs_subparsers.add_parser(
        "add", help="Add external documentation configuration"
    )
    doc_add_parser.add_argument("--name", required=True, help="Doc name")
    doc_add_parser.add_argument("--url", required=True, help="Doc URL")
    doc_add_parser.add_argument(
        "--allowlist-domain", help="Allowed domain pattern (optional)"
    )
    docs_subparsers.add_parser("refresh", help="Refresh external documentation cache")

    # Fix Error command
    fix_error_parser = subparsers.add_parser(
        "fix-error", help="Run automated error correction"
    )
    fix_error_parser.add_argument("--from-file", help="Path to error log file")
    fix_error_parser.add_argument(
        "--command", dest="run_command", help="Command to run that produces errors"
    )
    fix_error_parser.add_argument(
        "--dry-run", action="store_true", help="Generate patch without applying it"
    )
    fix_error_parser.add_argument("--workspace", help="Custom workspace path")
    add_provider_args(fix_error_parser)
    add_sandbox_args(fix_error_parser)
    add_policy_args(fix_error_parser)
    add_report_args(fix_error_parser)
    add_cache_args(fix_error_parser)
    add_execution_args(fix_error_parser)
    add_pricing_args(fix_error_parser)
    add_memory_args(fix_error_parser)
    add_agent_args(fix_error_parser)
    add_approval_args(fix_error_parser)
    add_checkpoint_args(fix_error_parser)
    add_auto_mode_args(fix_error_parser)

    # Terminal command
    terminal_parser = subparsers.add_parser("terminal", help="Terminal helper commands")
    terminal_parser.add_argument("--workspace", help="Custom workspace path")
    add_policy_args(terminal_parser)
    terminal_subparsers = terminal_parser.add_subparsers(
        dest="terminal_command", help="Terminal commands"
    )
    diagnose_parser = terminal_subparsers.add_parser(
        "diagnose", help="Diagnose last terminal command output"
    )
    diagnose_group = diagnose_parser.add_mutually_exclusive_group(required=True)
    diagnose_group.add_argument("--last-command", help="Last executed command")
    diagnose_group.add_argument(
        "--stderr-file", help="Path to a stderr log file to diagnose"
    )

    suggest_parser = terminal_subparsers.add_parser(
        "suggest", help="Suggest fix for command error from stderr log"
    )
    suggest_parser.add_argument("--stderr-file", required=True, help="Stderr log file path")

    # Multimodal command
    multimodal_parser = subparsers.add_parser("multimodal", help="Multimodal helper commands")
    multimodal_subparsers = multimodal_parser.add_subparsers(
        dest="multimodal_command", help="Multimodal commands"
    )
    inspect_parser = multimodal_subparsers.add_parser(
        "inspect", help="Inspect image file and return metadata"
    )
    inspect_parser.add_argument("image_path", help="Path to the image file")
    inspect_parser.add_argument("--workspace", help="Custom workspace path")

    complete_parser = subparsers.add_parser(
        "complete", help="Retrieve code completion suggestions"
    )
    complete_parser.add_argument("file_path", help="Path to the file to complete")
    complete_parser.add_argument(
        "--line", type=int, required=True, help="Cursor line (1-indexed)"
    )
    complete_parser.add_argument(
        "--column", type=int, required=True, help="Cursor column (0-indexed)"
    )
    complete_parser.add_argument("--workspace", help="Custom workspace path")
    add_provider_args(complete_parser)

    # IDE command
    ide_parser = subparsers.add_parser("ide", help="IDE integration and compatibility helper")
    ide_parser.add_argument("--workspace", help="Custom workspace path")
    ide_subparsers = ide_parser.add_subparsers(
        dest="ide_command", help="IDE commands"
    )
    import_parser = ide_subparsers.add_parser(
        "import-vscode", help="Import VS Code / Cursor configurations"
    )
    import_parser.add_argument(
        "--path", required=True, help="Path to VS Code config folder or file"
    )
    ide_subparsers.add_parser(
        "show-config", help="Show the imported configuration context"
    )

    # Models command
    models_parser = subparsers.add_parser("models", help="Model routing and profiles helper")
    models_subparsers = models_parser.add_subparsers(
        dest="models_command", help="Models commands"
    )
    models_subparsers.add_parser("list", help="List all configured model profiles")
    test_profile_parser = models_subparsers.add_parser("test", help="Test a model profile")
    test_profile_parser.add_argument("profile", help="Name of the model profile to test")

    # Teams command
    teams_parser = subparsers.add_parser("teams", help="Manage and inspect agent teams")
    teams_subparsers = teams_parser.add_subparsers(
        dest="teams_command", help="Teams commands"
    )
    teams_subparsers.add_parser("list", help="List all defined teams")
    inspect_team_parser = teams_subparsers.add_parser("inspect", help="Inspect a specific team")
    inspect_team_parser.add_argument("team_name", help="Name of the team to inspect")
    teams_subparsers.add_parser("validate", help="Validate agent registry and teams")
    
    run_team_parser = teams_subparsers.add_parser("run", help="Run a specific team task")
    run_team_parser.add_argument("team_name", help="Name of the team to run")
    run_team_parser.add_argument("--task", required=True, help="Task description")
    run_team_parser.add_argument(
        "--report", choices=["markdown", "json"], default="markdown", help="Report format"
    )
    add_provider_args(run_team_parser)
    add_sandbox_args(run_team_parser)

    inspect_run_parser = teams_subparsers.add_parser(
        "inspect-run", help="Inspect a specific team run"
    )
    inspect_run_parser.add_argument("run_id", help="ID of the run to inspect")

    # Autonomous command
    auto_parser = subparsers.add_parser("autonomous", help="Manage autonomous agent runs")
    auto_subparsers = auto_parser.add_subparsers(
        dest="autonomous_command", help="Autonomous commands"
    )
    
    run_auto_parser = auto_subparsers.add_parser("run", help="Start an autonomous run")
    run_auto_parser.add_argument("--goal", required=True, help="Autonomous goal")
    run_auto_parser.add_argument("--budget", type=float, help="Cost budget for the run")
    run_auto_parser.add_argument("--max-steps", type=int, default=50, help="Maximum steps")
    run_auto_parser.add_argument("--cooldown", type=int, default=60, help="Seconds between steps")
    add_provider_args(run_auto_parser)
    add_sandbox_args(run_auto_parser)

    auto_subparsers.add_parser("list", help="List all autonomous runs")
    
    inspect_auto_parser = auto_subparsers.add_parser(
        "inspect", help="Inspect a specific autonomous run"
    )
    inspect_auto_parser.add_argument("run_id", help="ID of the run to inspect")
    
    resume_auto_parser = auto_subparsers.add_parser("resume", help="Resume a paused autonomous run")
    resume_auto_parser.add_argument("run_id", help="ID of the run to resume")
    
    pause_auto_parser = auto_subparsers.add_parser("pause", help="Pause an active autonomous run")
    pause_auto_parser.add_argument("run_id", help="ID of the run to pause")
    
    stop_auto_parser = auto_subparsers.add_parser("stop", help="Stop an active autonomous run")
    stop_auto_parser.add_argument("run_id", help="ID of the run to stop")

    args = parser.parse_args()

    # Load dynamic plugins after argument parsing
    from .plugins import plugin_registry
    plugin_registry.load_all_plugins(enable_plugins=getattr(args, "enable_plugins", False))

    should_validate_config = not (
        args.command in ("health", "plugins", "benchmark")
        and getattr(args, "local_only", False)
        and not getattr(args, "config", None)
    )
    if should_validate_config:
        try:
            HarnessConfig.load_config(getattr(args, "config", None))
        except HarnessConfigError as exc:
            print(f"Configuration Error: {exc}", file=sys.stderr)
            if getattr(args, "debug", False):
                import traceback
                traceback.print_exc()
            sys.exit(1)

    try:
        if args.command == "health":
            asyncio.run(run_health_command(args))
        elif args.command == "server":
            run_server_command(args)
        elif args.command == "plugins":
            run_plugins_command(args)
        elif args.command == "benchmark":
            asyncio.run(run_benchmark_command(args))
        elif args.command == "code":
            asyncio.run(run_code_command(args))
        elif args.command == "code-batch":
            asyncio.run(run_code_batch_command(args))
        elif args.command == "security":
            run_security_command(args.check_only)
        elif args.command == "eval":
            asyncio.run(run_eval_command(args))
        elif args.command == "chat":
            asyncio.run(run_chat_command(args))
        elif args.command == "edit-inline":
            asyncio.run(run_edit_inline_command(args))
        elif args.command == "index":
            run_index_command(args)
        elif args.command == "docs":
            run_docs_command(args)
        elif args.command == "fix-error":
            asyncio.run(run_fix_error_command(args))
        elif args.command == "terminal":
            asyncio.run(run_terminal_command(args))
        elif args.command == "multimodal":
            run_multimodal_command(args)
        elif args.command == "complete":
            asyncio.run(run_complete_command(args))
        elif args.command == "ide":
            run_ide_command(args)
        elif args.command == "models":
            asyncio.run(run_models_command(args))
        elif args.command == "teams":
            asyncio.run(run_teams_command(args))
        elif args.command == "autonomous":
            asyncio.run(run_autonomous_command(args))
        else:
            parser.print_help()
    except HarnessConfigError as exc:
        print(f"Configuration Error: {exc}", file=sys.stderr)
        if getattr(args, "debug", False):
            import traceback
            traceback.print_exc()
        sys.exit(1)
    except ValueError as exc:
        print(f"ERROR: {Sanitizer.sanitize_text(str(exc))}")
        raise SystemExit(1) from exc

if __name__ == "__main__":
    main()
