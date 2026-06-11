from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Callable

from app.core.time import utc_now

from .models import (
    AgentGraphSpec,
    AgentNode,
    GraphEdge,
    GraphExecutionResult,
    GraphExecutionStatus,
    NodeExecutionResult,
    NodeExecutionStatus,
)

logger = logging.getLogger(__name__)


class AgentGraphEngine:
    """DAG-based agent graph execution engine.

    Processes a directed acyclic graph of agent nodes with:
    - Topological ordering & parallel execution
    - Retry with backoff
    - Checkpointing (save/restore)
    - Graceful cancellation
    - Dependency resolution
    """

    def __init__(
        self,
        artifacts_dir: str = "artifacts/agent-graphs",
        node_runner: Callable[[AgentNode, dict[str, Any]], Any] | None = None,
    ):
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._runner = node_runner
        self._running: dict[str, asyncio.Task] = {}
        self._cancel_flags: dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(
        self,
        graph: AgentGraphSpec,
        run_id: str | None = None,
        global_input: dict[str, Any] | None = None,
    ) -> GraphExecutionResult:
        run_id = run_id or str(uuid.uuid4())
        self._cancel_flags[run_id] = False
        checkpoint_dir = self.artifacts_dir / run_id / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        result = GraphExecutionResult(
            run_id=run_id,
            status=GraphExecutionStatus.RUNNING,
            started_at=utc_now().isoformat(),
            checkpoint_dir=str(checkpoint_dir),
        )

        try:
            task = asyncio.create_task(
                self._execute_graph(graph, run_id, checkpoint_dir, global_input, result)
            )
            self._running[run_id] = task
            await task
        except asyncio.CancelledError:
            result.status = GraphExecutionStatus.CANCELLED
            self._mark_pending_cancelled(result)
            logger.info("Graph run %s cancelled", run_id)
        except Exception as exc:
            result.status = GraphExecutionStatus.FAILED
            result.error = str(exc)
            logger.exception("Graph run %s failed: %s", run_id, exc)
        finally:
            result.completed_at = utc_now().isoformat()
            self._running.pop(run_id, None)
            self._cancel_flags.pop(run_id, None)

        self._persist_result(run_id, result)
        return result

    def cancel(self, run_id: str) -> bool:
        """Cancel a running graph execution."""
        if run_id in self._cancel_flags:
            self._cancel_flags[run_id] = True
            if run_id in self._running:
                self._running[run_id].cancel()
            return True
        return False

    def get_status(self, run_id: str) -> GraphExecutionResult | None:
        result_path = self.artifacts_dir / run_id / "result.json"
        if result_path.exists():
            return self._load_result(run_id)
        return None

    def list_runs(self) -> list[dict[str, Any]]:
        runs = []
        for d in self.artifacts_dir.iterdir():
            if d.is_dir():
                result_path = d / "result.json"
                if result_path.exists():
                    try:
                        data = json.loads(result_path.read_text())
                        runs.append({
                            "run_id": data.get("run_id"),
                            "status": data.get("status"),
                            "started_at": data.get("started_at"),
                            "completed_at": data.get("completed_at"),
                            "error": data.get("error"),
                        })
                    except Exception:
                        pass
        runs.sort(key=lambda r: r.get("started_at", ""), reverse=True)
        return runs

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    async def _execute_graph(
        self,
        graph: AgentGraphSpec,
        run_id: str,
        checkpoint_dir: Path,
        global_input: dict[str, Any] | None,
        result: GraphExecutionResult,
    ) -> None:
        # Build adjacency and in-degree maps
        adj: dict[str, list[GraphEdge]] = {n.id: [] for n in graph.nodes}
        in_degree: dict[str, int] = {n.id: 0 for n in graph.nodes}
        node_map: dict[str, AgentNode] = {n.id: n for n in graph.nodes}

        for edge in graph.edges:
            adj.setdefault(edge.source, []).append(edge)
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

        # Check for cycles
        if self._detect_cycle(node_map, adj):
            result.status = GraphExecutionStatus.FAILED
            result.error = "Graph contains a cycle"
            return

        # Restore from checkpoint if available
        checkpoint = self._load_checkpoint(run_id)
        if checkpoint:
            logger.info("Restoring graph %s from checkpoint", run_id)
            for node_id, node_result in checkpoint.get("node_results", {}).items():
                result.node_results[node_id] = NodeExecutionResult(**node_result)
                if node_result["status"] in ("completed", "skipped", "failed", "cancelled"):
                    in_degree[node_id] = -1  # mark as done

        # Topological processing with parallel execution
        ready = deque(
            nid for nid, deg in in_degree.items()
            if deg == 0 and nid not in result.node_results
        )
        semaphore = asyncio.Semaphore(graph.max_concurrency)
        pending: set[asyncio.Task] = set()

        while ready or pending:
            # Check for cancellation
            if self._cancel_flags.get(run_id):
                result.status = GraphExecutionStatus.CANCELLED
                self._mark_pending_cancelled(result)
                for t in pending:
                    t.cancel()
                return

            # Launch ready nodes
            while ready:
                node_id = ready.popleft()
                node = node_map[node_id]
                task = asyncio.create_task(
                    self._run_node_with_semaphore(
                        semaphore, node, global_input, result.node_results, run_id, checkpoint_dir
                    )
                )
                pending.add(task)
                task.add_done_callback(pending.discard)

            # Wait for at least one node to finish
            if pending:
                done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    completed_node_id = task.result()
                    if completed_node_id:
                        self._update_dependents(
                            completed_node_id, adj, in_degree, result.node_results, ready
                        )

            # Persist checkpoint after each wave
            if graph.enable_checkpointing:
                checkpoint = {
                    "node_results": {
                        nid: {
                            "node_id": nr.node_id,
                            "status": nr.status.value,
                            "output": nr.output,
                            "error": nr.error,
                            "duration_ms": nr.duration_ms,
                            "retry_attempts": nr.retry_attempts,
                            "checkpoint": nr.checkpoint,
                        }
                        for nid, nr in result.node_results.items()
                    }
                }
                self._save_checkpoint(run_id, checkpoint)

        # Final status
        all_completed = all(
            nr.status in (NodeExecutionStatus.COMPLETED, NodeExecutionStatus.SKIPPED)
            for nr in result.node_results.values()
        )
        result.status = (
            GraphExecutionStatus.COMPLETED if all_completed
            else GraphExecutionStatus.FAILED
        )

    async def _run_node_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        node: AgentNode,
        global_input: dict[str, Any] | None,
        node_results: dict[str, NodeExecutionResult],
        run_id: str,
        checkpoint_dir: Path,
    ) -> str:
        async with semaphore:
            result = await self._run_node(node, global_input, run_id, checkpoint_dir)
            node_results[node.id] = result
            return node.id if result.status == NodeExecutionStatus.COMPLETED else ""

    async def _run_node(
        self,
        node: AgentNode,
        global_input: dict[str, Any] | None,
        run_id: str,
        checkpoint_dir: Path,
    ) -> NodeExecutionResult:
        logger.info("Running node %s (%s)", node.id, node.type.value)
        start = time.perf_counter()
        last_error: str | None = None

        for attempt in range(node.max_retries + 1):
            if self._cancel_flags.get(run_id):
                return NodeExecutionResult(
                    node_id=node.id,
                    status=NodeExecutionStatus.CANCELLED,
                    error="Cancelled",
                    duration_ms=(time.perf_counter() - start) * 1000,
                    retry_attempts=attempt,
                )

            try:
                output = await asyncio.wait_for(
                    self._execute_node(node, global_input, run_id),
                    timeout=node.timeout_seconds,
                )
                duration = (time.perf_counter() - start) * 1000
                nr = NodeExecutionResult(
                    node_id=node.id,
                    status=NodeExecutionStatus.COMPLETED,
                    output=output or {},
                    duration_ms=duration,
                    retry_attempts=attempt,
                    checkpoint=self._build_checkpoint(node, output, run_id),
                )
                logger.info("Node %s completed in %.0fms", node.id, duration)
                return nr

            except asyncio.TimeoutError:
                last_error = f"Timeout after {node.timeout_seconds}s"
                logger.warning("Node %s timeout (attempt %d/%d)", node.id, attempt + 1, node.max_retries + 1)
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Node %s failed (attempt %d/%d): %s", node.id, attempt + 1, node.max_retries + 1, exc)

            if attempt < node.max_retries:
                await asyncio.sleep(2 ** attempt)  # exponential backoff

        duration = (time.perf_counter() - start) * 1000
        return NodeExecutionResult(
            node_id=node.id,
            status=NodeExecutionStatus.FAILED,
            error=last_error,
            duration_ms=duration,
            retry_attempts=node.max_retries,
        )

    async def _execute_node(
        self,
        node: AgentNode,
        global_input: dict[str, Any] | None,
        run_id: str,
    ) -> dict[str, Any]:
        if self._runner:
            return await self._runner(node, {"global_input": global_input, "run_id": run_id})
        return self._default_node_runner(node, global_input)

    def _default_node_runner(self, node: AgentNode, global_input: dict[str, Any] | None) -> dict[str, Any]:
        """Simulated node execution for testing."""
        import time as _time
        _time.sleep(0.05)  # simulate work
        return {
            "node_id": node.id,
            "type": node.type.value,
            "status": "ok",
            "summary": f"{node.type.value} completed task",
        }

    # ------------------------------------------------------------------
    # Topological sort & cycle detection
    # ------------------------------------------------------------------

    def _detect_cycle(self, node_map: dict[str, AgentNode], adj: dict[str, list[GraphEdge]]) -> bool:
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(nid: str) -> bool:
            if nid in rec_stack:
                return True
            if nid in visited:
                return False
            visited.add(nid)
            rec_stack.add(nid)
            for edge in adj.get(nid, []):
                if edge.target in node_map and dfs(edge.target):
                    return True
            rec_stack.remove(nid)
            return False

        return any(nid in node_map and dfs(nid) for nid in node_map)

    def topological_sort(self, graph: AgentGraphSpec) -> list[str]:
        adj: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
        in_degree: dict[str, int] = {n.id: 0 for n in graph.nodes}
        for edge in graph.edges:
            if edge.source in adj and edge.target in adj:
                adj[edge.source].append(edge.target)
                in_degree[edge.target] += 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order: list[str] = []
        while queue:
            nid = queue.popleft()
            order.append(nid)
            for neighbor in adj.get(nid, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        return order

    def _update_dependents(
        self,
        completed_node_id: str,
        adj: dict[str, list[GraphEdge]],
        in_degree: dict[str, int],
        node_results: dict[str, NodeExecutionResult],
        ready: deque,
    ) -> None:
        for edge in adj.get(completed_node_id, []):
            target = edge.target
            if target in in_degree and in_degree[target] > 0:
                in_degree[target] -= 1
                if in_degree[target] == 0 and target not in node_results:
                    ready.append(target)

    def _mark_pending_cancelled(self, result: GraphExecutionResult) -> None:
        for node_id, nr in result.node_results.items():
            if nr.status == NodeExecutionStatus.PENDING:
                nr.status = NodeExecutionStatus.CANCELLED

    # ------------------------------------------------------------------
    # Checkpointing
    # ------------------------------------------------------------------

    def _save_checkpoint(self, run_id: str, checkpoint: dict[str, Any]) -> None:
        ckpt_dir = self.artifacts_dir / run_id / "checkpoints"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        path = ckpt_dir / f"checkpoint_{int(time.time())}.json"
        path.write_text(json.dumps(checkpoint, indent=2, default=str))

    def _load_checkpoint(self, run_id: str) -> dict[str, Any] | None:
        ckpt_dir = self.artifacts_dir / run_id / "checkpoints"
        if not ckpt_dir.exists():
            return None
        checkpoints = sorted(ckpt_dir.glob("checkpoint_*.json"))
        if not checkpoints:
            return None
        try:
            return json.loads(checkpoints[-1].read_text())
        except Exception:
            return None

    def _build_checkpoint(self, node: AgentNode, output: dict[str, Any] | None, run_id: str) -> dict[str, Any]:
        return {
            "node_id": node.id,
            "type": node.type.value,
            "output": output,
            "timestamp": utc_now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_result(self, run_id: str, result: GraphExecutionResult) -> None:
        run_dir = self.artifacts_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "run_id": result.run_id,
            "status": result.status.value,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "error": result.error,
            "checkpoint_dir": result.checkpoint_dir,
            "node_results": {
                nid: {
                    "node_id": nr.node_id,
                    "status": nr.status.value,
                    "output": nr.output,
                    "error": nr.error,
                    "duration_ms": nr.duration_ms,
                    "retry_attempts": nr.retry_attempts,
                }
                for nid, nr in result.node_results.items()
            },
        }
        (run_dir / "result.json").write_text(json.dumps(data, indent=2, default=str))

    def _load_result(self, run_id: str) -> GraphExecutionResult:
        data = json.loads((self.artifacts_dir / run_id / "result.json").read_text())
        node_results = {}
        for nid, nd in data.get("node_results", {}).items():
            node_results[nid] = NodeExecutionResult(
                node_id=nd["node_id"],
                status=NodeExecutionStatus(nd["status"]),
                output=nd.get("output", {}),
                error=nd.get("error"),
                duration_ms=nd.get("duration_ms", 0),
                retry_attempts=nd.get("retry_attempts", 0),
            )
        return GraphExecutionResult(
            run_id=data["run_id"],
            status=GraphExecutionStatus(data["status"]),
            node_results=node_results,
            error=data.get("error"),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            checkpoint_dir=data.get("checkpoint_dir", ""),
        )
