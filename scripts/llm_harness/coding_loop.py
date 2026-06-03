import asyncio
import hashlib
import json
import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from ._security import SecurityManager
from .agent_client import AgentClient
from .approval import ApprovalProvider
from .cache import LocalCache
from .checkpoint import CheckpointManager
from .context import ContextManager
from .defaults import MAX_OUTPUT_CHARS, WORKSPACE_MOUNT_PATH
from .heal import HealEngine
from .memory import LocalMemory
from .metrics import MetricsManager
from .models import ExecutionResult, HarnessEvent
from .patcher import Patcher
from .policy import PolicyEngine
from .pricing import PricingManager
from .prompt_builder import PromptBuilder
from .sandbox import SandboxRunner
from .sanitizer import Sanitizer
from .tokenizer import TokenCounter
from .tools.editor import EditorTools
from .tools.files import FileTools
from .tools.search import SearchTools
from .tools.shell import ShellTools
from .tools.tests import TestTools
from .tracing import Tracer
from .webhooks import WebhookManager
from .workspace import Workspace

logger = logging.getLogger(__name__)


class CodingLoop:
    """
    Orquestra o processo iterativo: Pensar -> Agir -> Observar -> Corrigir.
    Coordena Workspace, Sandbox, Patcher, PolicyEngine e eventos de progresso.
    """

    def __init__(
        self,
        agent_client: AgentClient,
        workspace: Workspace,
        timeout: int = 300,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        use_docker: bool = False,
        docker_image: str = "python:3.12-slim",
        self_heal: bool = True,
        max_steps: int = 5,
        test_command: str = "pytest",
        allow_test_short_circuit: bool = False,
        workspace_mount_path: str = WORKSPACE_MOUNT_PATH,
        sandbox_network: str = "none",
        proxy_url: str | None = None,
        max_output_chars: int = MAX_OUTPUT_CHARS,
        cache: LocalCache | None = None,
        pricing_file: str | None = None,
        max_cost: float | None = None,
        max_tokens: int | None = None,
        memory_mode: str = "local",
        memory_dir: str = ".llm_harness_memory",
        memory_retention_days: int = 30,
        approval_mode: str = "auto",
        approval_default: str = "deny",
        checkpoint_dir: str = ".llm_harness_checkpoints",
        checkpoint_every_step: bool = False,
    ):
        self.agent_client = agent_client
        self.allow_test_short_circuit = allow_test_short_circuit
        self.workspace = workspace
        self.timeout = timeout
        self.progress_callback = progress_callback
        self.self_heal = self_heal
        self.max_steps = max(1, max_steps)
        self.cache = cache
        self.max_parallel_actions = 2 # Default limit

        policy_config = {}
        if max_cost is not None:
            policy_config["max_cost"] = max_cost
        if max_tokens is not None:
            policy_config["max_tokens"] = max_tokens

        self.policy_engine = PolicyEngine(config=policy_config)
        self.pricing_manager = PricingManager(pricing_file=pricing_file)

        self.tokenizer = TokenCounter(method="auto")
        self.context_manager = ContextManager(
            max_context_tokens=max_tokens or 4096,
            reserved_output_tokens=1024,
            token_counter=self.tokenizer,
            summarize_func=self._summarize_content
        )

        self.memory = None
        if memory_mode == "local":
            self.memory = LocalMemory(
                memory_dir=memory_dir,
                retention_days=memory_retention_days
            )

        self.approval_provider = ApprovalProvider(
            mode=approval_mode,
            default_policy=approval_default
        )

        self.checkpoint_mgr = CheckpointManager(checkpoint_dir=checkpoint_dir)
        self.checkpoint_every_step = checkpoint_every_step
        self.run_id = str(uuid.uuid4())

        self.policy_summary = self.policy_engine.describe_for_agent()

        memory_context = ""
        eval_feedback = ""
        if self.memory:
            memory_context = self.memory.get_context_for_prompt()
            eval_feedback = self.memory.get_latest_eval_feedback() or ""

        self.prompt_builder = PromptBuilder(
            policy_summary=self.policy_summary,
            memory_context=memory_context,
            eval_feedback=eval_feedback
        )
        self.policy_hash = (
            self.cache.compute_policy_hash(self.policy_summary) if self.cache else "no-policy"
        )
        self.sandbox = SandboxRunner(
            workspace=workspace,
            use_docker=use_docker,
            docker_image=docker_image,
            workspace_mount_path=workspace_mount_path,
            network_mode=sandbox_network,
            proxy_url=proxy_url,
        )
        self.patcher = Patcher(workspace=workspace, policy_engine=self.policy_engine)
        self.file_tools = FileTools(
            workspace=workspace,
            policy_engine=self.policy_engine,
            cache=self.cache,
            repo_snapshot_hash_getter=self._get_repo_snapshot_hash,
            policy_hash=self.policy_hash,
        )
        self.search_tools = SearchTools(workspace=workspace, policy_engine=self.policy_engine)
        self.editor_tools = EditorTools(workspace=workspace, policy_engine=self.policy_engine)
        from .tools.git import GitTools

        self.git_tools = GitTools(
            workspace=workspace,
            policy_engine=self.policy_engine,
            cache=self.cache,
            repo_snapshot_hash_getter=self._get_repo_snapshot_hash,
            policy_hash=self.policy_hash,
        )
        self.shell_tools = ShellTools(
            sandbox_runner=self.sandbox,
            policy_engine=self.policy_engine,
            output_limit=max_output_chars,
            cache=self.cache,
            repo_snapshot_hash_getter=self._get_repo_snapshot_hash,
            policy_hash=self.policy_hash,
            git_tools=self.git_tools,
        )
        self.test_tools = TestTools(sandbox=self.sandbox, test_command=test_command)
        self.heal_engine = HealEngine()

        # Instrumentation
        self.metrics = MetricsManager()
        self.tracer = Tracer()
        self.webhooks = WebhookManager(
            url=self.policy_engine.config.get("webhook_url"),
            enabled_events=self.policy_engine.config.get("webhook_events")
        )

        self.history: list[dict[str, Any]] = []
        self.blocked_actions: list[str] = []
        self.events: list[dict[str, Any]] = []
        self.trace: list[dict[str, Any]] = []
        self.trace_id: str | None = None
        self.run_span_id: str | None = None
        self.provider: str = "openai-compatible"
        self._event_step = 0

        # Performance Metrics
        self.total_duration_ms = 0.0
        self.command_duration_ms = 0.0
        self.agent_latency_ms = 0.0
        self.retry_count = 0
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.estimated_cost = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
        self.llm_calls = 0
        self.changed_files: set[str] = set()
        self.model: str = ""

        # LLM API retry config
        self._llm_max_retries = 3
        self._llm_retry_base_delay = 1.0

    def get_state(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "history": self.history,
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_cost": self.estimated_cost,
            "llm_calls": self.llm_calls,
            "step": self._event_step,
            "changed_files": list(self.changed_files),
        }

    def load_state(self, state: dict[str, Any]):
        self.run_id = state.get("run_id", self.run_id)
        self.history = state.get("history", [])
        self.total_tokens = state.get("total_tokens", 0)
        self.prompt_tokens = state.get("prompt_tokens", 0)
        self.completion_tokens = state.get("completion_tokens", 0)
        self.estimated_cost = state.get("estimated_cost", 0.0)
        self.llm_calls = state.get("llm_calls", 0)
        self._event_step = state.get("step", 0)
        self.changed_files = set(state.get("changed_files", []))

    async def _summarize_content(self, content: str) -> str:
        """
        Summarizes long content using the LLM.
        """
        if len(content) <= 1000:
            return content

        summary_prompt = (
            "Summarize the following tool output or file content concisely, "
            "preserving only key information (errors, success markers, or critical data):\n\n"
            f"{content[:5000]}" # Limit input to avoid infinite recursion/token limits
        )

        try:
            # We use a direct call to the agent client to avoid the full coding loop overhead
            response = await self.agent_client.chat_completion([
                {"role": "user", "content": summary_prompt}
            ])
            summary = response["choices"][0]["message"]["content"].strip()
            return f"[Summarized Output]: {summary}"
        except Exception as e:
            logger.error(f"LLM Summarization failed: {e}")
            return content[:800] + "\n... [TRUNCATED DUE TO SUMMARIZATION ERROR] ..."

    def _get_repo_snapshot_hash(self) -> str:
        if not self.cache:
            return "no-cache"
        return self.cache.compute_repo_snapshot_hash(self.workspace.path)

    def _hash_payload(self, payload: Any) -> str:
        sanitized = Sanitizer.sanitize_data(payload)
        encoded = json.dumps(sanitized, sort_keys=True, ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _policy_payload(self, decision: Any) -> dict[str, Any]:
        if hasattr(decision, "model_dump"):
            return Sanitizer.sanitize_data(decision.model_dump())
        if isinstance(decision, dict):
            return Sanitizer.sanitize_data(decision)
        return {
            "allowed": True,
            "reason": None,
            "policy_level": "internal",
            "policy_rule": "implicit-allow",
        }

    def _record_trace(
        self,
        action_type: str,
        step: int,
        input_payload: Any,
        output_payload: Any,
        policy_decision: Any,
        tool_result: Any,
    ) -> None:
        if not self.trace_id:
            self.trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        entry = {
            "action_id": f"{self.trace_id}:{step}:{action_type}",
            "action_type": action_type,
            "step": step,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "input": Sanitizer.sanitize_data(input_payload),
            "output": Sanitizer.sanitize_data(output_payload),
            "input_hash": self._hash_payload(input_payload),
            "output_hash": self._hash_payload(output_payload),
            "policy_decision": self._policy_payload(policy_decision),
            "tool_result_hash": self._hash_payload(tool_result),
        }
        self.trace.append(entry)

    def _build_result(
        self,
        *,
        success: bool,
        duration: float,
        message: str | None = None,
        error: str | None = None,
    ) -> ExecutionResult:
        # End instrumentation
        self.metrics.end_run(success=success)
        if hasattr(self, "run_span_id") and self.run_span_id:
            self.tracer.end_span(self.run_span_id, success=success, error=error)
            self.run_span_id = None

        trace_hash = self._hash_payload(self.trace) if self.trace else None
        return ExecutionResult(
            success=success,
            message=message,
            error=error,
            trace_id=self.trace_id,
            trace_hash=trace_hash,
            duration=duration,
            total_duration_ms=duration * 1000,
            command_duration_ms=self.command_duration_ms,
            agent_latency_ms=self.agent_latency_ms,
            retry_count=self.retry_count,
            total_tokens=self.total_tokens,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            llm_calls=self.llm_calls,
            llm_provider=self.provider,
            llm_model=self.model,
            estimated_cost=getattr(self, "estimated_cost", 0.0),
            cache_hits=getattr(self, "cache_hits", 0),
            cache_misses=getattr(self, "cache_misses", 0),
            metrics=self.metrics.to_dict(),
            events=list(self.events),
            trace=list(self.trace),
        )

    def _emit_event(
        self,
        event: str,
        action_type: str | None = None,
        status: str | None = None,
        message: str | None = None,
        duration_ms: float = 0,
        agent_latency_ms: float = 0,
        metadata: dict[str, Any] | None = None,
        step: int | None = None,
    ) -> dict[str, Any]:

        if step is None:
            self._event_step += 1
            step = self._event_step
        else:
            self._event_step = max(self._event_step, step)

        trace_id = self.trace_id or (
            self.tracer.get_trace_id() if hasattr(self, "tracer") else "no-trace"
        )
        payload = HarnessEvent(
            event=event,
            trace_id=trace_id,
            action_type=action_type,
            step=step,
            status=status,
            duration_ms=max(0, int(duration_ms)),
            agent_latency_ms=max(0, int(agent_latency_ms)),
            message=Sanitizer.sanitize_text(message) if message else "",
            metadata=Sanitizer.sanitize_data(metadata or {}),
        ).model_dump()
        self.events.append(payload)

        # Send webhook if manager is available
        if hasattr(self, "webhooks"):
            asyncio.create_task(self.webhooks.send_event(event, payload))

        if self.progress_callback:
            self.progress_callback(payload)
        return payload

    async def _run_action(
        self,
        action_type: str,
        func: Callable[..., Any],
        *args: Any,
        metadata: dict[str, Any] | None = None,
        failure_message: Callable[[Any], str | None] | None = None,
        **kwargs: Any,
    ) -> Any:
        start = time.perf_counter()
        step = self._event_step + 1
        self._emit_event(
            "action.started",
            action_type=action_type,
            status="started",
            message=f"{action_type} started",
            metadata=metadata,
            step=step,
        )
        try:
            with self.tracer.trace_span("tool_call", attributes={"action_type": action_type}):
                result = func(*args, **kwargs)
                if hasattr(result, "__await__"):
                    result = await result

            # Record tool call in metrics
            # Note: run_shell handles its own metrics to account for cache
            if action_type != "run_shell":
                self.metrics.record_tool_call(cached=False)

            duration_ms = int((time.perf_counter() - start) * 1000)
            self.command_duration_ms += duration_ms
            if failure_message:
                maybe_error = failure_message(result)
                if maybe_error:
                    heal_info = {}
                    if self.self_heal:
                        heal_info = self.heal_engine.analyze_error(maybe_error)

                    self._emit_event(
                        "action.failed",
                        action_type=action_type,
                        status="failed",
                        message=maybe_error,
                        duration_ms=duration_ms,
                        metadata={**(metadata or {}), **heal_info},
                        step=step,
                    )
                    raise RuntimeError(maybe_error)
            self._emit_event(
                "action.completed",
                action_type=action_type,
                status="completed",
                message=f"{action_type} completed",
                duration_ms=duration_ms,
                metadata=metadata,
                step=step,
            )
            return result
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            self.command_duration_ms += duration_ms

            heal_info = {}
            if self.self_heal:
                heal_info = self.heal_engine.analyze_error(str(exc))

            self._emit_event(
                "action.failed",
                action_type=action_type,
                status="failed",
                message=str(exc),
                duration_ms=duration_ms,
                metadata={**(metadata or {}), **heal_info},
                step=step,
            )
            raise

    def _format_tool_result(
        self,
        action_type: str,
        success: bool,
        output: str = "",
        error: str = "",
    ) -> str:
        """Format a tool execution result as a message for the LLM."""
        status = "SUCCESS" if success else "FAILED"
        parts = [f"[Tool Result: {action_type}] Status: {status}"]
        if output:
            limit = (
                self.shell_tools.output_limit
                if hasattr(self.shell_tools, "output_limit")
                else 10000
            )
            truncated = output[:limit]
            if len(output) > len(truncated):
                truncated += f"\n... (truncated, {len(output)} total chars)"
            parts.append(f"Output:\n{truncated}")
        if error:
            parts.append(f"Error: {error}")
        return Sanitizer.sanitize_text("\n".join(parts))

    def _append_tool_result(
        self, action_type: str, success: bool, output: str = "", error: str = ""
    ) -> None:
        """Append a tool execution result to conversation history for the LLM to observe."""
        content = self._format_tool_result(action_type, success, output, error)
        self.history.append({"role": "user", "content": content})

    async def _chat_completion_with_retry(self) -> dict[str, Any]:
        """Call chat_completion with retry and exponential backoff for transient errors."""
        from .utils.retry import async_retry

        self.agent_client.set_cache_context(
            repo_snapshot_hash=self._get_repo_snapshot_hash(),
            policy_hash=self.policy_hash,
        )

        managed_history = await self.context_manager.manage_context(self.history)
        ctx_metrics = self.context_manager.get_metrics()
        self._emit_event(
            "context.managed",
            action_type="context",
            metadata=ctx_metrics
        )

        class _ClientError(Exception):
            pass

        async def _do_chat():
            with self.tracer.trace_span(
                "llm_call", attributes={"model": self.agent_client.model}
            ):
                return await self.agent_client.chat_completion(managed_history)

        try:
            response = await async_retry(
                _do_chat,
                max_retries=self._llm_max_retries,
                base_delay=self._llm_retry_base_delay,
            )
        except Exception as exc:
            error_str = str(exc).lower()
            is_client_error = any(code in error_str for code in ("401", "403", "404", "422"))
            if is_client_error:
                raise
            raise

        self.llm_calls += 1
        self.policy_engine.record_llm_call()

        usage = response.get("usage", {})
        t_tokens = 0
        p_tokens = 0
        c_tokens = 0
        if isinstance(usage, dict):
            t_tokens = usage.get("total_tokens", 0) or 0
            p_tokens = usage.get("prompt_tokens", 0) or 0
            c_tokens = usage.get("completion_tokens", 0) or 0
            self.total_tokens += t_tokens
            self.prompt_tokens += p_tokens
            self.completion_tokens += c_tokens

        cost_result = self.pricing_manager.calculate_cost(
            model=self.agent_client.model,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens
        )
        cost_value = cost_result.cost if cost_result is not None else 0.0
        if cost_result is not None:
            self.estimated_cost += cost_result.cost

        self.metrics.record_llm_call(
            tokens=t_tokens,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            cost=cost_value,
        )

        if not self.model and self.agent_client.model:
            self.model = self.agent_client.model

        if not self.policy_engine.check_usage(self.total_tokens, self.estimated_cost):
            self._emit_event(
                "policy.blocked",
                action_type="chat_completion",
                status="blocked",
                message="Usage limit exceeded",
                metadata={"tokens": self.total_tokens, "cost": self.estimated_cost},
            )
            raise PermissionError("Usage limit exceeded")

        return response

    def _emit_policy_blocked(
        self, action_type: str, message: str, metadata: dict[str, Any] | None = None
    ):
        self.blocked_actions.append(Sanitizer.sanitize_text(message))
        self._emit_event(
            "policy.blocked",
            action_type=action_type,
            status="blocked",
            message=message,
            metadata=metadata,
        )

    async def read_file(self, path: str) -> str:
        decision = self.policy_engine.evaluate_file_path(path)
        step = self._event_step + 1
        if not decision.allowed:
            self._emit_policy_blocked(
                "read_file",
                decision.reason or "Path blocked by policy",
                metadata={"path": path},
            )
            self._record_trace(
                "read_file",
                step,
                {"path": path},
                {"blocked": True, "reason": decision.reason},
                decision,
                {"blocked": True, "reason": decision.reason},
            )
            raise PermissionError(decision.reason or "Path blocked by policy")
        result = await self._run_action(
            "read_file", self.file_tools.read_file, path, metadata={"path": path}
        )
        self._record_trace(
            "read_file",
            step,
            {"path": path},
            {"content": result},
            decision,
            {"content": result},
        )
        return result

    async def apply_patch(self, diff_content: str, dry_run: bool = False):
        step = self._event_step + 1
        result = await self._run_action(
            "apply_patch",
            self.patcher.apply_patch,
            diff_content,
            dry_run=dry_run,
            metadata={"dry_run": dry_run},
            failure_message=lambda result: result.error if not result.success else None,
        )
        if result.success and not dry_run:
            self.changed_files.update(result.changed_files)
            self.metrics.record_changed_files(result.changed_files)
        self._record_trace(
            "apply_patch",
            step,
            {"dry_run": dry_run, "diff_sha256": result.diff_sha256},
            {
                "success": result.success,
                "changed_files": result.changed_files,
                "mode": result.mode,
                "diff_sha256": result.diff_sha256,
            },
            {"allowed": result.success, "reason": result.error, "policy_level": "patch"},
            result.model_dump(),
        )
        return result

    async def run_shell(self, command: str, timeout: int = 30):
        start = time.perf_counter()
        step = self._event_step + 1
        metadata = {"command": command}
        self._emit_event(
            "action.started",
            action_type="run_shell",
            status="started",
            message="run_shell started",
            metadata=metadata,
            step=step,
        )
        try:
            result = await self.shell_tools.run_shell_async(command, timeout=timeout)
            is_cached = getattr(result, "cached", False)
            self.metrics.record_tool_call(cached=is_cached)

            if hasattr(result, "cached"):
                if result.cached:
                    self.cache_hits += 1
                else:
                    self.cache_misses += 1
            duration_ms = int((time.perf_counter() - start) * 1000)
            self.command_duration_ms += duration_ms
            if result.blocked:
                self._emit_policy_blocked(
                    "run_shell",
                    result.reason or "Command blocked by policy",
                    metadata=metadata,
                )
                self._record_trace(
                    "run_shell",
                    step,
                    {"command": command, "timeout": timeout},
                    {"blocked": True, "reason": result.reason},
                    result.policy_decision,
                    {
                        "blocked": True,
                        "reason": result.reason,
                        "returncode": result.returncode,
                    },
                )
                raise PermissionError(result.reason or "Command blocked by policy")
            if result.returncode != 0:
                heal_info = {}
                if self.self_heal:
                    heal_info = self.heal_engine.analyze_error(result.output or "")

                self._emit_event(
                    "action.failed",
                    action_type="run_shell",
                    status="failed",
                    message=result.output or f"Command failed with exit code {result.returncode}",
                    duration_ms=duration_ms,
                    metadata={
                        "command": command,
                        "returncode": result.returncode,
                        "parsed": result.parsed.to_dict(),
                        "cached": result.cached,
                        **heal_info,
                    },
                    step=step,
                )
                self._record_trace(
                    "run_shell",
                    step,
                    {"command": command, "timeout": timeout},
                    {
                        "returncode": result.returncode,
                        "output": result.output,
                        "cached": result.cached,
                    },
                    result.policy_decision,
                    {
                        "returncode": result.returncode,
                        "output": result.output,
                        "parsed": result.parsed.to_dict(),
                        "cached": result.cached,
                    },
                )
                raise RuntimeError(
                    result.output or f"Command failed with exit code {result.returncode}"
                )
            self._emit_event(
                "action.completed",
                action_type="run_shell",
                status="completed",
                message=result.parsed.summary or "run_shell completed",
                duration_ms=duration_ms,
                metadata={**metadata, "parsed": result.parsed.to_dict(), "cached": result.cached},
                step=step,
            )
            self._record_trace(
                "run_shell",
                step,
                {"command": command, "timeout": timeout},
                {
                    "returncode": result.returncode,
                    "output": result.output,
                    "cached": result.cached,
                },
                result.policy_decision,
                {
                    "returncode": result.returncode,
                    "output": result.output,
                    "parsed": result.parsed.to_dict(),
                    "cached": result.cached,
                },
            )
            return result
        except PermissionError:
            raise
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            self.command_duration_ms += duration_ms

            heal_info = {}
            if self.self_heal:
                heal_info = self.heal_engine.analyze_error(str(exc))

            existing = [
                event
                for event in self.events
                if event["step"] == step and event["event"] == "action.failed"
            ]
            if not existing:
                self._emit_event(
                    "action.failed",
                    action_type="run_shell",
                    status="failed",
                    message=str(exc),
                    duration_ms=duration_ms,
                    metadata={**(metadata or {}), **heal_info},
                    step=step,
                )
            raise

    async def run_tests(self, test_path: str = "tests/") -> dict[str, Any]:
        step = self._event_step + 1
        result = await self._run_action(
            "run_tests",
            self.test_tools.run_pytest,
            test_path,
            metadata={"test_path": test_path},
            failure_message=lambda result: (
                result.get("error") or result.get("output") or "Tests failed"
            )
            if not result.get("success", False)
            else None,
        )
        self._record_trace(
            "run_tests",
            step,
            {"test_path": test_path},
            result,
            {"allowed": True, "policy_level": "internal", "policy_rule": "test-run"},
            result,
        )
        return result

    async def final(self, message: str) -> str:
        step = self._event_step + 1
        result = await self._run_action(
            "final", lambda: message, metadata={"provider": self.provider}
        )
        self._record_trace(
            "final",
            step,
            {"message": message},
            {"message": result},
            {"allowed": True, "policy_level": "internal", "policy_rule": "final"},
            {"message": result},
        )
        return result

    async def plan(self, message: str = "", reason: str = "") -> str:
        summary = message or reason or "Plan acknowledged"
        step = self._event_step + 1
        result = await self._run_action(
            "plan",
            lambda: summary,
            metadata={"reason": reason, "message": message},
        )
        self._record_trace(
            "plan",
            step,
            {"message": message, "reason": reason},
            {"summary": result},
            {"allowed": True, "policy_level": "internal", "policy_rule": "plan"},
            {"summary": result},
        )
        return result

    async def _execute_single_action(self, action: dict[str, Any]) -> Any:
        if not self.approval_provider.request_approval(action):
            logger.warning(f"Action {action.get('action_type')} denied by user approval")
            raise PermissionError(f"Action {action.get('action_type')} denied by user approval")

        action_type = action.get("action_type")
        if action_type == "plan":
            return await self.plan(action.get("message", ""), action.get("reason", ""))
        elif action_type == "read_file":
            return await self.read_file(action["path"])
        elif action_type == "grep":
            return self.search_tools.grep(
                action["pattern"],
                path=action.get("path", "."),
                regex=action.get("regex", False),
                recursive=action.get("recursive", True)
            )
        elif action_type == "ast_search":
            return self.search_tools.ast_search(
                action["symbol_name"],
                path=action.get("path", ".")
            )
        elif action_type == "find_replace":
            return self.editor_tools.find_replace(
                action["filename"],
                action["find_str"],
                action["replace_str"]
            )
        elif action_type == "insert_after":
            return self.editor_tools.insert_after(
                action["filename"],
                action["anchor"],
                action["content"]
            )
        elif action_type == "apply_patch":
            return await self.apply_patch(action["diff"], dry_run=action.get("dry_run", False))
        elif action_type == "run_shell":
            return await self.run_shell(action["command"], timeout=action.get("timeout", 30))
        elif action_type == "run_tests":
            return await self.run_tests(action.get("test_path", "tests/"))
        elif action_type == "final":
            return await self.final(action.get("message", "Loop finished"))
        elif action_type == "parallel":
            sub_actions = action.get("actions", [])
            return await self._execute_parallel_actions(sub_actions)
        else:
            from .plugins import plugin_registry
            if action_type in plugin_registry.list_tools():
                tool_callable = plugin_registry.list_tools()[action_type]
                res = tool_callable(
                    action,
                    context={
                        "coding_loop": self,
                        "workspace": self.workspace,
                        "sandbox": self.sandbox,
                    },
                )
                if hasattr(res, "__await__"):
                    return await res
                return res
            raise ValueError(f"Unsupported action_type: {action_type}")

    async def _execute_parallel_actions(self, actions: list[dict[str, Any]]) -> list[Any]:
        # Only allow read-only actions in parallel
        allowed_parallel = {
            "read_file", "plan", "search", "grep", "ast_search", "git_status", "git_diff"
        }

        # Note: 'search', 'grep', 'git_status', 'git_diff' might be mapped to 'run_shell'
        # but if the agent uses them as action_type, we should support them if they are implemented.
        # Currently they seem to be mostly via 'run_shell'.

        for action in actions:
            action_type = action.get("action_type")
            if action_type not in allowed_parallel:
                raise ValueError(
                    f"Action type '{action_type}' is not allowed in parallel mode "
                    "(side-effects restricted)"
                )

        tasks = [self._execute_single_action(a) for a in actions]
        results = []
        for i in range(0, len(tasks), self.max_parallel_actions):
            chunk = tasks[i : i + self.max_parallel_actions]
            results.extend(await asyncio.gather(*chunk))
        return results

    async def _execute_action_plan(self, action_plan: list[dict[str, Any]]) -> str | None:
        final_message = None
        for action in action_plan:
            res = await self._execute_single_action(action)
            if action.get("action_type") == "final":
                final_message = res
        return final_message

    def _parse_agent_actions(self, content: str) -> tuple[list[dict[str, Any]] | None, str | None]:
        cleaned = content.strip()
        if cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned[3:-3].strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            return None, None

        if isinstance(payload, list):
            return payload, None
        if isinstance(payload, dict):
            if "actions" in payload and isinstance(payload["actions"], list):
                return payload["actions"], payload.get("final")
            if "action_type" in payload:
                return [payload], payload.get("final")
            if isinstance(payload.get("final"), str):
                return [], payload["final"]
        return None, None

    async def run(
        self,
        task: str | list[dict[str, Any]],
        action_plan: list[dict[str, Any]] | None = None,
    ) -> ExecutionResult:
        result = await self._run_inner(task, action_plan)
        if self.memory:
            task_str = json.dumps(task) if isinstance(task, list) else task
            self.memory.record_run(task_str, result.model_dump())
        return result

    async def _run_inner(
        self,
        task: str | list[dict[str, Any]],
        action_plan: list[dict[str, Any]] | None = None,
    ) -> ExecutionResult:
        start_time = time.time()
        logger.info(f"Starting coding loop for task: {task}")

        # Instrumentation
        self.metrics.start_run()
        self.run_span_id = self.tracer.start_span("run", attributes={"task": task})

        # Reset per-run state
        self.events = []
        self.trace = []
        self.trace_id = self.tracer.get_trace_id()
        self._event_step = 0
        self.history = []
        self.blocked_actions = []
        self.command_duration_ms = 0.0
        self.agent_latency_ms = 0.0
        self.retry_count = 0
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.estimated_cost = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
        self.llm_calls = 0
        self.changed_files = set()
        self.heal_engine.reset_counts()

        self._emit_event(
            "run.started",
            action_type="loop",
            status="started",
            message=f"Starting coding loop for task: {task}",
            metadata={"provider": self.provider, "changed_files": list(self.changed_files)},
        )

        system_prompt = self.prompt_builder.build_system_prompt()
        self.history.append({"role": "system", "content": system_prompt})
        user_prompt = self.prompt_builder.build_task_prompt(task)
        self.history.append({"role": "user", "content": user_prompt})

        try:
            for _i in range(self.max_steps):
                if time.time() - start_time > self.timeout:
                    return ExecutionResult(
                        **self._build_result(
                            success=False,
                            error="Execution timeout exceeded",
                            duration=time.time() - start_time,
                        ).model_dump()
                    )

                agent_start = time.perf_counter()
                response = await self._chat_completion_with_retry()
                agent_lat = int((time.perf_counter() - agent_start) * 1000)
                self.agent_latency_ms += agent_lat

                content = response["choices"][0]["message"]["content"]
                sanitized_content = SecurityManager.sanitize_output(content)
                self.history.append({"role": "assistant", "content": sanitized_content})

                if action_plan:
                    try:
                        final_message = await self._execute_action_plan(action_plan)
                        self._append_tool_result(
                            "action_plan", True, output=final_message or "Plan executed"
                        )

                    except Exception as exc:
                        self._append_tool_result("action_plan", False, error=str(exc))
                        raise
                    duration = time.time() - start_time
                    self._emit_event(
                        "run.completed",
                        action_type="loop",
                        status="completed",
                        message=final_message or "Loop finished",
                        duration_ms=int(duration * 1000),
                        metadata={
                            "provider": self.provider,
                            "changed_files": list(self.changed_files),
                        },
                    )
                    return ExecutionResult(
                        **self._build_result(
                            success=True,
                            message=final_message or "Loop finished",
                            duration=duration,
                        ).model_dump()
                    )

                parsed_actions, final_message = self._parse_agent_actions(sanitized_content)
                if parsed_actions is not None:
                    final_already_executed = False
                    final_from_actions = None
                    if parsed_actions:
                        action_results: list[str] = []
                        try:
                            final_from_actions = await self._execute_action_plan(parsed_actions)
                            final_already_executed = any(
                                action.get("action_type") == "final" for action in parsed_actions
                            )
                            final_message = final_from_actions or final_message
                            # Feed back tool results to LLM
                            for action in parsed_actions:
                                atype = action.get("action_type", "unknown")
                                if atype != "final":
                                    action_results.append(f"{atype}: completed")
                            if action_results:
                                self._append_tool_result(
                                    "actions", True,
                                    output="\n".join(action_results),
                                )
                        except PermissionError as exc:
                            self._append_tool_result("actions", False, error=str(exc))
                            raise
                        except Exception as exc:
                            # Feed error back to LLM so it can self-correct
                            self._append_tool_result("actions", False, error=str(exc))
                            # Don't re-raise — let the loop continue so the LLM can try to fix
                            logger.warning(f"Action failed, feeding error to LLM: {exc}")
                            continue

                    if final_already_executed:
                        msg = final_from_actions or final_message or "Loop finished"
                        duration = time.time() - start_time
                        self._emit_event(
                            "run.completed",
                            action_type="loop",
                            status="completed",
                            message=msg,
                            duration_ms=int(duration * 1000),
                            metadata={
                                "provider": self.provider,
                                "changed_files": list(self.changed_files),
                            },
                        )
                        return ExecutionResult(
                            **self._build_result(
                                success=True,
                                message=msg,
                                duration=duration,
                            ).model_dump()
                        )

                    if self.checkpoint_every_step:
                        self.checkpoint_mgr.save_checkpoint(self.run_id, self.get_state())

                    if final_message:
                        msg = (
                            final_message
                            if final_already_executed
                            else await self.final(final_message)
                        )
                        duration = time.time() - start_time
                        self._emit_event(
                            "run.completed",
                            action_type="loop",
                            status="completed",
                            message=msg,
                            duration_ms=int(duration * 1000),
                            metadata={
                                "provider": self.provider,
                                "changed_files": list(self.changed_files),
                            },
                        )
                        return ExecutionResult(
                            **self._build_result(
                                success=True,
                                message=msg,
                                duration=duration,
                            ).model_dump()
                        )
                    continue

                task_str_lower = (
                    task.lower() if isinstance(task, str) else str(task).lower()
                )
                if (
                    self.allow_test_short_circuit
                    and self.provider == "stub"
                    and "fix" in task_str_lower
                ):
                    msg = await self.final("Task completed (simulated)")
                    duration = time.time() - start_time
                    self._emit_event(
                        "run.completed",
                        action_type="loop",
                        status="completed",
                        message=msg,
                        duration_ms=int(duration * 1000),
                        metadata={
                            "provider": self.provider,
                            "changed_files": list(self.changed_files),
                        },
                    )
                    return ExecutionResult(
                        **self._build_result(
                            success=True,
                            message=msg,
                            duration=duration,
                        ).model_dump()
                    )

                # LLM returned non-JSON content — this is a failure, not success
                logger.warning("LLM returned unparseable response, ending loop with failure")
                duration = time.time() - start_time
                self._emit_event(
                    "run.completed",
                    action_type="loop",
                    status="failed",
                    message="LLM returned unparseable response",
                    duration_ms=int(duration * 1000),
                    metadata={"provider": self.provider, "changed_files": list(self.changed_files)},
                )
                return ExecutionResult(
                    **self._build_result(
                        success=False,
                        error="LLM returned unparseable response",
                        duration=duration,
                    ).model_dump()
                )

            # max_steps exhausted without a final message
            duration = time.time() - start_time
            self._emit_event(
                "run.completed",
                action_type="loop",
                status="completed",
                message="Loop finished (max steps reached)",
                duration_ms=int(duration * 1000),
                metadata={"provider": self.provider, "changed_files": list(self.changed_files)},
            )
            return ExecutionResult(
                **self._build_result(
                    success=False,
                    error="Loop finished without completing task (max steps reached)",
                    duration=duration,
                ).model_dump()
            )
        except PermissionError as exc:
            duration = time.time() - start_time
            self._emit_event(
                "run.failed",
                action_type="loop",
                status="failed",
                message=str(exc),
                duration_ms=int(duration * 1000),
            )
            return ExecutionResult(
                **self._build_result(
                    success=False,
                    error=Sanitizer.sanitize_text(str(exc)),
                    duration=duration,
                ).model_dump()
            )
        except Exception as exc:
            logger.exception("Coding loop failed")
            duration = time.time() - start_time
            self._emit_event(
                "run.failed",
                action_type="loop",
                status="failed",
                message=str(exc),
                duration_ms=int(duration * 1000),
            )
            return ExecutionResult(
                **self._build_result(
                    success=False,
                    error=Sanitizer.sanitize_text(str(exc)),
                    duration=duration,
                ).model_dump()
            )
