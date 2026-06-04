import argparse
import asyncio
import logging
import os
import sys
from typing import Any, Literal, cast

from ._logging import setup_logging
from .agent_client import AgentClient
from .cache import CacheMode, LocalCache
from .checkpoint import CheckpointManager
from .coding_loop import CodingLoop
from .config import HarnessConfig, HarnessConfigError
from .defaults import (
    MAX_OUTPUT_CHARS,
    REPORT_OUTPUT_PATH,
    TEMP_BASE_DIR,
    WORKSPACE_MOUNT_PATH,
)
from .models import ExecutionResult
from .multi_agent import MultiAgentOrchestrator
from .sanitizer import Sanitizer
from .workspace import Workspace


async def run_harness(
    agent_id: str = "default-coder",
    task: str = "",
    timeout: int = 300,
    workspace_path: str | None = None,
    provider: str = "openai-compatible",
    allow_stub: bool = False,
    progress_callback=None,
    use_docker: bool = False,
    docker_image: str = "python:3.12-slim",
    base_url: str = "",
    self_heal: bool = True,
    model: str = "",
    api_key_env: str = "OPENAI_API_KEY",
    test_command: str = "pytest",
    max_steps: int = 5,
    request_timeout: float = 30.0,
    local_model_timeout: float = 300.0,
    auto_increase_timeout: bool = False,
    max_retries: int = 3,
    stream: bool = False,
    stream_local_default: bool = True,
    verbose_stream: bool = False,
    tool_calling: str = "auto",
    supports_tool_calling: bool = False,
    allow_test_short_circuit: bool = False,
    workspace_mount_path: str = WORKSPACE_MOUNT_PATH,
    temp_base_dir: str | None = TEMP_BASE_DIR,
    sandbox_network: str = "none",
    proxy_url: str | None = None,
    max_output_chars: int = MAX_OUTPUT_CHARS,
    report_output_path: str = REPORT_OUTPUT_PATH,
    cache_mode: CacheMode = "disabled",
    cache_dir: str = ".llm_harness_cache",
    pricing_file: str | None = None,
    max_cost: float | None = None,
    max_tokens: int | None = None,
    memory_mode: str = "local",
    memory_dir: str = ".llm_harness_memory",
    memory_retention_days: int = 30,
    agent_mode: str = "single",
    approval_mode: str = "auto",
    approval_default: str = "deny",
    edit_action_before_run: bool = False,
    checkpoint_dir: str = ".llm_harness_checkpoints",
    checkpoint_every_step: bool = False,
    resume_run_id: str | None = None,
    config: HarnessConfig | None = None,
    image_path: str | None = None,
    audio_path: str | None = None,
    video_path: str | None = None,
    multimodal: bool = False,
) -> ExecutionResult:
    """
    Run the LLM Harness.

    .. deprecated:: 1.0.0
       Use run_harness with a HarnessConfig instance passed to the `config` parameter instead.
    """
    setup_logging()
    logger = logging.getLogger("agent_harness")

    if config is None:
        import warnings
        warnings.warn(
            "Passing individual parameters to run_harness is deprecated. "
            "Pass a HarnessConfig instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        config = HarnessConfig(
            code_agent=agent_id,
            provider=provider,
            model=model,
            base_url=base_url,
            api_key_env=api_key_env,
            sandbox=use_docker,
            docker_image=docker_image,
            test_command=test_command,
            max_steps=max_steps,
            self_heal=self_heal,
            timeout=request_timeout,
            local_model_timeout=local_model_timeout,
            auto_increase_timeout=auto_increase_timeout,
            max_retries=max_retries,
            stream=stream,
            stream_local_default=stream_local_default,
            verbose_stream=verbose_stream,
            tool_calling=cast(Literal["auto", "native", "json"], tool_calling),
            supports_tool_calling=supports_tool_calling,
            workspace_mount_path=workspace_mount_path,
            temp_base_dir=temp_base_dir,
            loop_timeout=timeout,
            max_output_chars=max_output_chars,
            report_output_path=report_output_path,
            sandbox_network=cast(Literal["none", "host", "proxy"], sandbox_network),
            proxy_url=proxy_url,
            cache=cache_mode,
            cache_dir=cache_dir,
            pricing_file=pricing_file,
            max_cost_per_run=max_cost,
            max_tokens_per_run=max_tokens,
            memory=cast(Literal["disabled", "local"], memory_mode),
            memory_dir=memory_dir,
            memory_retention_days=memory_retention_days,
            agent_mode=cast(Literal["single", "planner-coder-reviewer"], agent_mode),
            approval_mode=cast(
                Literal["auto", "deny", "interactive", "non_interactive"], approval_mode
            ),
            approval_default=cast(Literal["allow", "deny"], approval_default),
            edit_action_before_run=edit_action_before_run,
            checkpoint_dir=checkpoint_dir,
            checkpoint_every_step=checkpoint_every_step,
            multimodal=multimodal,
            audio_path=audio_path,
            video_path=video_path,
        )
    else:
        provider = config.provider or config.code_agent

    if provider == "stub":
        msg = "WARNING: code agent provider is stub; no real task execution will be performed."
        logger.warning(msg)
        if not allow_stub:
            err = "Stub provider not allowed without --allow-stub-code-agent"
            return ExecutionResult(success=False, error=err)

    logger.info(f"Initializing harness for agent {config.code_agent} (Provider: {provider})")

    async with Workspace(base_path=workspace_path, temp_base_dir=config.temp_base_dir) as ws:
        cache = LocalCache(mode=config.cache, cache_dir=config.cache_dir)
        client = AgentClient(
            agent_id=config.code_agent,
            base_url=config.base_url,
            provider=provider,
            model=config.model,
            api_key_env=config.api_key_env,
            timeout=config.timeout,
            local_model_timeout=config.local_model_timeout,
            auto_increase_timeout=config.auto_increase_timeout,
            max_retries=config.max_retries,
            stream=config.stream,
            stream_local_default=config.stream_local_default,
            verbose_stream=config.verbose_stream,
            tool_calling=config.tool_calling,
            supports_tool_calling=config.supports_tool_calling,
            allow_native_tools_for_local=config.allow_native_tools_for_local,
            lm_studio_compatibility=config.lm_studio_compatibility,
            capability_cache_ttl_seconds=config.capability_cache_ttl_seconds,
            cache=cache,
            multimodal=config.multimodal,
            max_tokens=config.max_tokens,
            event_callback=progress_callback,
        )

        task_content: str | list[dict[str, Any]] = task

        def _validate_and_load_media(file_path: str, media_type: str) -> tuple[str, str]:
            if not config.multimodal:
                raise ValueError(
                    "Provider or model does not support multimodal input. "
                    "Enable 'multimodal' or choose a multimodal model."
                )
            from .policy import PolicyEngine
            temp_pe = PolicyEngine()
            dec = temp_pe.evaluate_file_path(file_path)
            if not dec.allowed:
                raise PermissionError(f"{media_type} path blocked by policy: {dec.reason}")

            abs_path = os.path.abspath(os.path.join(ws.path, file_path))
            ws_abs = os.path.abspath(ws.path)
            if not abs_path.startswith(ws_abs):
                raise PermissionError(
                    f"{media_type} path {file_path} is outside the workspace repository."
                )
            if not os.path.exists(abs_path):
                raise FileNotFoundError(f"{media_type} not found at path: {file_path}")

            import base64
            with open(abs_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")
            ext = os.path.splitext(abs_path)[1].lower().strip(".")
            return ext, b64_data

        def _load_image(file_path: str) -> dict[str, Any]:
            ext, b64_data = _validate_and_load_media(file_path, "Image")
            mime = f"image/{ext}" if ext in ("png", "jpeg", "jpg", "webp", "gif") else "image/png"
            return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_data}"}}

        def _load_audio(file_path: str) -> dict[str, Any]:
            ext, b64_data = _validate_and_load_media(file_path, "Audio")
            mime_map = {
                "mp3": "audio/mpeg", "wav": "audio/wav",
                "ogg": "audio/ogg", "flac": "audio/flac",
            }
            mime = mime_map.get(ext, "audio/mpeg")
            return {
                "type": "audio_url",
                "audio_url": {"url": f"data:{mime};base64,{b64_data}"},
                "metadata": {"mime_type": mime, "extension": ext},
            }

        def _load_video(file_path: str) -> dict[str, Any]:
            ext, b64_data = _validate_and_load_media(file_path, "Video")
            mime_map = {
                "mp4": "video/mp4", "webm": "video/webm",
                "avi": "video/x-msvideo", "mov": "video/quicktime",
            }
            mime = mime_map.get(ext, "video/mp4")
            return {
                "type": "video_url",
                "video_url": {"url": f"data:{mime};base64,{b64_data}"},
                "metadata": {"mime_type": mime, "extension": ext},
            }

        media_blocks = []
        effective_audio = audio_path or getattr(config, "audio_path", None)
        effective_video = video_path or getattr(config, "video_path", None)
        if image_path:
            media_blocks.append(_load_image(image_path))
        if effective_audio:
            media_blocks.append(_load_audio(effective_audio))
        if effective_video:
            media_blocks.append(_load_video(effective_video))
        if media_blocks:
            task_content = [{"type": "text", "text": task}] + media_blocks

        loop = CodingLoop(
            agent_client=client,
            workspace=ws,
            timeout=config.loop_timeout,
            progress_callback=progress_callback,
            use_docker=config.sandbox,
            docker_image=config.docker_image,
            self_heal=config.self_heal,
            max_steps=config.max_steps,
            test_command=config.test_command,
            allow_test_short_circuit=allow_test_short_circuit,
            workspace_mount_path=config.workspace_mount_path,
            sandbox_network=config.sandbox_network,
            proxy_url=config.proxy_url,
            max_output_chars=config.max_output_chars,
            cache=cache,
            pricing_file=config.pricing_file,
            max_cost=config.max_cost_per_run,
            max_tokens=config.max_tokens,
            max_tokens_per_run=config.max_tokens_per_run,
            memory_mode=config.memory,
            memory_dir=config.memory_dir,
            memory_retention_days=config.memory_retention_days,
            approval_mode=config.approval_mode,
            approval_default=config.approval_default,
            edit_action_before_run=config.edit_action_before_run,
            checkpoint_dir=config.checkpoint_dir,
            checkpoint_every_step=config.checkpoint_every_step,
            is_reasoning_model=config.is_reasoning_model,
        )
        loop.provider = provider  # Pass provider to loop for reporting
        loop.model = config.model  # Pass model name to loop for metrics

        if resume_run_id:
            checkpoint_mgr = CheckpointManager(checkpoint_dir=config.checkpoint_dir)
            state = checkpoint_mgr.load_checkpoint(resume_run_id)
            if state:
                loop.load_state(state)
                logger.info(f"Resuming from checkpoint {resume_run_id}")
            else:
                return ExecutionResult(success=False, error=f"Checkpoint {resume_run_id} not found")

        try:
            loop.config = config
            from .mcp import initialize_mcp_and_register_tools, mcp_client
            mcp_client.enabled = config.mcp.enabled
            mcp_client.servers_config = [s.model_dump() for s in config.mcp.servers]
            await initialize_mcp_and_register_tools(loop.policy_engine)

            if getattr(config, "auto", False):
                from .auto_mode import AutoModeRunner
                runner = AutoModeRunner(
                    coding_loop=loop,
                    max_auto_fixes=getattr(config, "max_auto_fixes", 3),
                    stop_on_risk=getattr(config, "stop_on_risk", False),
                    require_approval_for_edits=getattr(config, "require_approval_for_edits", False),
                )
                result = await runner.run_task(task=task_content)
            elif config.agent_mode == "planner-coder-reviewer":
                orchestrator = MultiAgentOrchestrator(coding_loop=loop)
                result = await orchestrator.run_planner_coder_reviewer(task=task_content)
            elif config.agent_mode == "supervisor":
                orchestrator = MultiAgentOrchestrator(coding_loop=loop)
                result = await orchestrator.run_supervisor(task=task_content)
            else:
                result = await loop.run(task=task_content)

            if result.success:
                logger.info("Task completed successfully")
            else:
                logger.error(f"Task failed: {result.error}")

            if mcp_client.enabled and mcp_client.mcp_logs:
                result.metrics["mcp_calls"] = list(mcp_client.mcp_logs)

            return result
        except Exception as e:
            logger.exception("Unexpected error during execution")
            return ExecutionResult(success=False, error=Sanitizer.sanitize_text(str(e)))
        finally:
            from .mcp import mcp_client
            await mcp_client.shutdown()


def main():
    parser = argparse.ArgumentParser(description="LLM Harness Orchestrator")
    parser.add_argument("--config", help="Path to custom config file")
    parser.add_argument("--debug", action="store_true", help="Show verbose stack traces on error")
    parser.add_argument("--agent-id", required=True, help="ID of the agent")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds")
    parser.add_argument("--workspace", help="Custom workspace path")
    parser.add_argument(
        "--code-agent",
        "--provider",
        dest="provider",
        default="openai-compatible",
        choices=[
            "stub",
            "openai-compatible",
            "local-openai-compatible",
            "anthropic",
            "google",
            "control-plane",
        ],
        help="Agent provider",
    )
    parser.add_argument("--sandbox", action="store_true", help="Enable sandbox")
    parser.add_argument("--docker-image", default="python:3.12-slim", help="Docker image")
    parser.add_argument("--base-url", default="", help="Base URL")
    parser.add_argument("--model", default="", help="LLM model")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY", help="API key env var")
    parser.add_argument("--request-timeout", type=float, default=30.0, help="HTTP timeout")
    parser.add_argument("--max-retries", type=int, default=3, help="HTTP retries")
    parser.add_argument(
        "--no-self-heal",
        action="store_false",
        dest="self_heal",
        default=True,
        help="Disable self-heal",
    )
    parser.add_argument("--allow-stub-code-agent", action="store_true", help="Allow stub provider")
    parser.add_argument(
        "--allow-test-short-circuit",
        action="store_true",
        help="Allow short-circuiting task execution for tests",
    )
    parser.add_argument(
        "--workspace-mount-path",
        default=WORKSPACE_MOUNT_PATH,
        help="Workspace mount path inside docker container",
    )
    parser.add_argument(
        "--temp-base-dir",
        default=TEMP_BASE_DIR,
        help="Temporary base directory for workspace creation",
    )
    parser.add_argument(
        "--max-output-chars",
        type=int,
        default=MAX_OUTPUT_CHARS,
        help="Maximum characters of shell tool output before truncation",
    )
    parser.add_argument(
        "--report-output-path",
        default=REPORT_OUTPUT_PATH,
        help="Report output directory",
    )

    args = parser.parse_args()

    try:
        HarnessConfig.load_config(getattr(args, "config", None))
    except HarnessConfigError as exc:
        print(f"Configuration Error: {exc}", file=sys.stderr)
        if getattr(args, "debug", False):
            import traceback
            traceback.print_exc()
        sys.exit(1)

    res = asyncio.run(
        run_harness(
            task=args.task,
            allow_stub=args.allow_stub_code_agent,
            allow_test_short_circuit=args.allow_test_short_circuit,
            workspace_path=args.workspace,
            config=HarnessConfig(
                code_agent=args.agent_id,
                provider=args.provider,
                sandbox=args.sandbox,
                docker_image=args.docker_image,
                base_url=args.base_url,
                self_heal=args.self_heal,
                model=args.model,
                api_key_env=args.api_key_env,
                test_command="pytest",
                max_steps=5,
                timeout=args.request_timeout,
                max_retries=args.max_retries,
                workspace_mount_path=args.workspace_mount_path,
                temp_base_dir=args.temp_base_dir,
                loop_timeout=args.timeout,
                max_output_chars=args.max_output_chars,
                report_output_path=args.report_output_path,
            ),
        )
    )

    if res.success:
        print(f"SUCCESS: {res.message}")
        sys.exit(0)
    else:
        print(f"FAILED: {res.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
