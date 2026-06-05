import asyncio
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from app.services.auth import require_admin
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

HARNESS_IMPORT_ERROR: Exception | None = None


def _ensure_harness_import_paths() -> None:
    current = Path(__file__).resolve()
    candidates = [
        current.parents[2],  # container runtime: /app
        current.parents[3],  # source tree: repo root
    ]
    for candidate in candidates:
        candidate_str = str(candidate)
        if not (candidate / "scripts").exists():
            continue
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


_ensure_harness_import_paths()

try:
    from scripts.llm_harness.config import HarnessConfig
    from scripts.llm_harness.evals.loader import EvalLoader
    from scripts.llm_harness.evals.runner import EvalRunner
    from scripts.llm_harness.legacy_runner import run_harness
    from scripts.llm_harness.providers import create_code_agent
    from scripts.llm_harness.providers import _PROVIDER_REGISTRY
    from scripts.llm_harness.sanitizer import Sanitizer
    HARNESS_RUNTIME_AVAILABLE = True
except ModuleNotFoundError as exc:
    HarnessConfig = None  # type: ignore[assignment]
    EvalLoader = None  # type: ignore[assignment]
    EvalRunner = None  # type: ignore[assignment]
    run_harness = None  # type: ignore[assignment]
    create_code_agent = None  # type: ignore[assignment]
    _PROVIDER_REGISTRY = {}  # type: ignore[assignment]
    Sanitizer = None  # type: ignore[assignment]
    HARNESS_RUNTIME_AVAILABLE = False
    HARNESS_IMPORT_ERROR = exc

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/harness",
    tags=["admin", "harness"],
    dependencies=[Depends(require_admin)],
)

ACTIVE_RUNS: dict[str, dict[str, Any]] = {}
ACTIVE_EVAL_RUNS: dict[str, dict[str, Any]] = {}
MAX_CONCURRENT_RUNS = 4
MAX_EVENTS_PER_RUN = 10_000
RUN_TTL_SECONDS = 3600  # clean up completed runs after 1 hour
RUN_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_RUNS)
RUN_SEMAPHORE_RELEASED: set[str] = set()
EVAL_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_RUNS)
EVAL_SEMAPHORE_RELEASED: set[str] = set()


def _evict_stale_runs() -> None:
    now = time.time()
    stale_ids = [
        run_id
        for run_id, data in ACTIVE_RUNS.items()
        if data["status"] != "running" and now - data.get("finished_at", now) > RUN_TTL_SECONDS
    ]
    for run_id in stale_ids:
        ACTIVE_RUNS.pop(run_id, None)
    stale_eval_ids = [
        run_id
        for run_id, data in ACTIVE_EVAL_RUNS.items()
        if data["status"] != "running" and now - data.get("finished_at", now) > RUN_TTL_SECONDS
    ]
    for run_id in stale_eval_ids:
        ACTIVE_EVAL_RUNS.pop(run_id, None)


def require_harness_runtime() -> None:
    if HARNESS_RUNTIME_AVAILABLE:
        return
    detail = "LLM Harness runtime unavailable in control-plane container"
    if HARNESS_IMPORT_ERROR is not None:
        detail = f"{detail}: {HARNESS_IMPORT_ERROR}"
    raise HTTPException(status_code=503, detail=detail)


class HarnessRunRequest(BaseModel):
    task: str
    agent_id: str = "default-coder"
    workspace: str | None = None
    provider: str = "stub"
    model: str = ""
    tags: list[str] = Field(default_factory=list)
    webhook_url: str | None = None
    config_overrides: dict[str, Any] = Field(default_factory=dict)

    @field_validator("task")
    @classmethod
    def validate_task(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("task must not be empty")
        if len(value) > 100_000:
            raise ValueError("task exceeds maximum length of 100,000 characters")
        return value

    @field_validator("config_overrides")
    @classmethod
    def validate_local_provider_config(cls, value: dict[str, Any], info: Any) -> dict[str, Any]:
        provider = info.data.get("provider", "")
        if provider == "local-openai-compatible" and not str(value.get("base_url", "")).strip():
            raise ValueError("config_overrides.base_url is required for provider local-openai-compatible")
        return value


class HarnessEvalRunRequest(BaseModel):
    suite_path: str
    concurrency: int = Field(default=1, ge=1, le=8)
    provider: str = "stub"
    model: str = ""
    config_overrides: dict[str, Any] = Field(default_factory=dict)

    @field_validator("suite_path")
    @classmethod
    def validate_suite_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("suite_path must not be empty")
        return value

    @field_validator("config_overrides")
    @classmethod
    def validate_local_provider_config(cls, value: dict[str, Any], info: Any) -> dict[str, Any]:
        provider = info.data.get("provider", "")
        if provider == "local-openai-compatible" and not str(value.get("base_url", "")).strip():
            raise ValueError("config_overrides.base_url is required for provider local-openai-compatible")
        return value


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy" if HARNESS_RUNTIME_AVAILABLE else "degraded",
        "runtime_available": HARNESS_RUNTIME_AVAILABLE,
        "runtime_error": str(HARNESS_IMPORT_ERROR) if HARNESS_IMPORT_ERROR else None,
        "active_runs": sum(1 for run in ACTIVE_RUNS.values() if run["status"] == "running"),
        "active_eval_runs": sum(1 for run in ACTIVE_EVAL_RUNS.values() if run["status"] == "running"),
        "max_concurrent_runs": MAX_CONCURRENT_RUNS,
    }


@router.post("/runs")
async def create_run(req: HarnessRunRequest) -> dict[str, str]:
    require_harness_runtime()
    if RUN_SEMAPHORE.locked():
        raise HTTPException(status_code=503, detail="Too many concurrent runs")
    await RUN_SEMAPHORE.acquire()

    _evict_stale_runs()

    run_id = str(uuid.uuid4())
    ACTIVE_RUNS[run_id] = {
        "run_id": run_id,
        "task": req.task,
        "status": "running",
        "events": [],
        "listeners": [],
        "result": None,
        "error": None,
        "task_handle": None,
        "created_at": time.time(),
        "finished_at": None,
    }

    def progress_callback(event: dict[str, Any]) -> None:
        run_data = ACTIVE_RUNS.get(run_id)
        if not run_data:
            return
        if len(run_data["events"]) >= MAX_EVENTS_PER_RUN:
            return
        run_data["events"].append(event)
        for queue in list(run_data["listeners"]):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    config_overrides = {
        "code_agent": req.agent_id,
        "provider": req.provider,
        "model": req.model,
        **req.config_overrides,
    }

    async def run_in_background() -> None:
        try:
            result = await run_harness(
                task=req.task,
                progress_callback=progress_callback,
                workspace_path=req.workspace,
                allow_stub=True,
                config=HarnessConfig(**config_overrides),  # type: ignore[misc]
            )
            run_data = ACTIVE_RUNS.get(run_id)
            if run_data:
                run_data["status"] = "completed" if result.success else "failed"
                run_data["result"] = result
        except asyncio.CancelledError:
            run_data = ACTIVE_RUNS.get(run_id)
            if run_data:
                run_data["status"] = "cancelled"
            raise
        except Exception as exc:
            logger.exception("Harness run failed")
            run_data = ACTIVE_RUNS.get(run_id)
            if run_data:
                run_data["status"] = "failed"
                run_data["error"] = str(exc)
        finally:
            if run_id not in RUN_SEMAPHORE_RELEASED:
                RUN_SEMAPHORE.release()
                RUN_SEMAPHORE_RELEASED.add(run_id)
            run_data = ACTIVE_RUNS.get(run_id)
            if run_data:
                run_data["finished_at"] = time.time()
                for queue in list(run_data["listeners"]):
                    try:
                        queue.put_nowait(None)
                    except asyncio.QueueFull:
                        pass

    task_handle = asyncio.create_task(run_in_background())
    ACTIVE_RUNS[run_id]["task_handle"] = task_handle
    return {"run_id": run_id, "status": "running"}


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    require_harness_runtime()
    run_data = ACTIVE_RUNS.get(run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Run not found")

    result = run_data["result"]
    sanitized_result = None
    if result is not None:
        sanitized_result = Sanitizer.sanitize_data(result.model_dump())  # type: ignore[union-attr]

    return {
        "run_id": run_id,
        "task": run_data["task"],
        "status": run_data["status"],
        "error": run_data["error"],
        "result": sanitized_result,
        "events": Sanitizer.sanitize_data(list(run_data["events"])),  # type: ignore[union-attr]
        "created_at": run_data.get("created_at"),
        "finished_at": run_data.get("finished_at"),
    }


@router.get("/runs/{run_id}/events")
async def get_run_events(run_id: str) -> StreamingResponse:
    require_harness_runtime()
    run_data = ACTIVE_RUNS.get(run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        for event in list(run_data["events"]):
            yield f"data: {json.dumps(Sanitizer.sanitize_data(event))}\n\n"  # type: ignore[union-attr]

        if run_data["status"] != "running":
            return

        if len(run_data["listeners"]) >= 16:
            raise HTTPException(status_code=429, detail="Too many event listeners for this run")
        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=1024)
        run_data["listeners"].append(queue)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(Sanitizer.sanitize_data(event))}\n\n"  # type: ignore[union-attr]
        finally:
            if queue in run_data["listeners"]:
                run_data["listeners"].remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str) -> dict[str, str]:
    require_harness_runtime()
    run_data = ACTIVE_RUNS.get(run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Run not found")

    if run_data["status"] == "running" and run_data.get("task_handle") is not None:
        run_data["task_handle"].cancel()
        run_data["status"] = "cancelled"
        run_data["finished_at"] = time.time()
        for queue in list(run_data["listeners"]):
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass
    return {"status": run_data["status"]}


@router.get("/runs")
async def list_runs(limit: int = 50, offset: int = 0) -> dict[str, list[dict[str, Any]]]:
    require_harness_runtime()
    _evict_stale_runs()
    runs = []
    for run_id, data in ACTIVE_RUNS.items():
        runs.append({
            "run_id": run_id,
            "task": data["task"][:200],
            "status": data["status"],
            "created_at": data.get("created_at"),
            "finished_at": data.get("finished_at"),
            "error": data.get("error"),
        })
    runs.sort(key=lambda r: r.get("created_at") or 0, reverse=True)
    return {"runs": runs[offset:offset + limit]}


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str) -> dict[str, str]:
    require_harness_runtime()
    run_data = ACTIVE_RUNS.get(run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Run not found")
    if run_data["status"] == "running":
        run_data["task_handle"].cancel()
        for queue in list(run_data["listeners"]):
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass
        if run_id not in RUN_SEMAPHORE_RELEASED:
            RUN_SEMAPHORE.release()
            RUN_SEMAPHORE_RELEASED.add(run_id)
    ACTIVE_RUNS.pop(run_id, None)
    RUN_SEMAPHORE_RELEASED.discard(run_id)
    return {"status": "deleted"}


@router.get("/providers")
async def list_providers() -> dict[str, list[str]]:
    require_harness_runtime()
    return {"providers": sorted(_PROVIDER_REGISTRY.keys())}


@router.get("/providers/{provider_name}/models")
async def list_provider_models(
    provider_name: str,
    base_url: str = "",
    model: str = "",
    api_key_env: str = "OPENAI_API_KEY",
) -> dict[str, Any]:
    require_harness_runtime()
    if provider_name not in _PROVIDER_REGISTRY:
        raise HTTPException(status_code=404, detail="Provider not found")
    if provider_name in {"local-openai-compatible", "openai-compatible", "control-plane"} and not base_url.strip():
        raise HTTPException(status_code=422, detail="base_url is required for this provider")

    try:
        agent = create_code_agent(  # type: ignore[misc]
            provider_name,
            {
                "agent_id": "harness-model-discovery",
                "provider": provider_name,
                "base_url": base_url.strip(),
                "model": model.strip(),
                "api_key_env": api_key_env,
                "stream": False,
                "tool_calling": "json",
            },
        )
        health = await agent.health_check()
    except Exception as exc:
        detail = Sanitizer.sanitize_text(str(exc)) if Sanitizer is not None else str(exc)
        raise HTTPException(status_code=502, detail=detail) from exc

    details = health.get("details", {})
    return {
        "provider": provider_name,
        "status": health.get("status"),
        "models": details.get("available_models", []),
        "selected_model": details.get("selected_model"),
        "models_url": details.get("models_url"),
        "supports_native_tool_calling": details.get("supports_native_tool_calling"),
        "auto_selected_model": details.get("auto_selected_model"),
    }


@router.get("/tools")
async def list_tools() -> dict[str, list[dict[str, str]]]:
    require_harness_runtime()
    tools = [
        {"name": "plan", "description": "Update or create execution plan"},
        {"name": "read_file", "description": "Read file contents"},
        {"name": "grep", "description": "Search text patterns"},
        {"name": "ast_search", "description": "Search source code symbols"},
        {"name": "find_replace", "description": "Replace text in file"},
        {"name": "insert_after", "description": "Insert text after anchor"},
        {"name": "apply_patch", "description": "Apply unidiff to workspace"},
        {"name": "run_shell", "description": "Run shell command in sandbox"},
        {"name": "run_tests", "description": "Run test suite"},
        {"name": "final", "description": "Submit final completion message"},
        {"name": "parallel", "description": "Run multiple actions concurrently"},
    ]
    try:
        from scripts.llm_harness.plugins import plugin_registry

        for name, tool_class in plugin_registry.list_tools().items():
            tools.append({"name": name, "description": f"Plugin tool: {tool_class.__name__}"})
    except Exception:
        logger.debug("Plugin registry unavailable for harness tools", exc_info=True)

    try:
        from scripts.llm_harness.mcp import mcp_client

        if mcp_client.is_enabled():
            for name, tool in mcp_client.list_tools().items():
                tools.append(
                    {
                        "name": f"mcp:{name}",
                        "description": str(tool.get("description", "MCP tool")),
                    }
                )
    except Exception:
        logger.debug("MCP registry unavailable for harness tools", exc_info=True)

    return {"tools": tools}


@router.get("/evals")
async def list_eval_suites(evals_dir: str = "examples/llm_harness/evals") -> dict[str, list[str]]:
    require_harness_runtime()
    files: list[str] = []
    if os.path.isdir(evals_dir):
        for filename in os.listdir(evals_dir):
            if filename.endswith(".eval_suite.json") or filename.endswith(".eval_suite.yaml"):
                files.append(filename)
    return {"eval_suites": sorted(files)}


@router.post("/evals/runs")
async def create_eval_run(req: HarnessEvalRunRequest) -> dict[str, str]:
    require_harness_runtime()
    _evict_stale_runs()
    if EVAL_SEMAPHORE.locked():
        raise HTTPException(status_code=503, detail="Too many concurrent eval runs")
    await EVAL_SEMAPHORE.acquire()
    eval_run_id = str(uuid.uuid4())
    ACTIVE_EVAL_RUNS[eval_run_id] = {
        "eval_run_id": eval_run_id,
        "status": "running",
        "result": None,
        "error": None,
        "events": [],
        "listeners": [],
        "created_at": time.time(),
        "finished_at": None,
    }

    def eval_progress_callback(event: dict[str, Any]) -> None:
        run_data = ACTIVE_EVAL_RUNS.get(eval_run_id)
        if not run_data:
            return
        run_data["events"].append(event)
        for queue in list(run_data["listeners"]):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def run_eval_in_background() -> None:
        try:
            suite = EvalLoader.load(req.suite_path)  # type: ignore[union-attr]
            runner = EvalRunner(  # type: ignore[misc]
                suite=suite,
                provider=req.provider or "stub",
                model=req.model or "",
                allow_stub=True,
                progress_callback=eval_progress_callback,
                **req.config_overrides,
            )
            result = await runner.run_all(concurrency=req.concurrency)
            run_data = ACTIVE_EVAL_RUNS.get(eval_run_id)
            if run_data:
                run_data["status"] = "completed"
                run_data["result"] = result
        except Exception as exc:
            logger.exception("Harness eval run failed")
            run_data = ACTIVE_EVAL_RUNS.get(eval_run_id)
            if run_data:
                run_data["status"] = "failed"
                run_data["error"] = str(exc)
        finally:
            if eval_run_id not in EVAL_SEMAPHORE_RELEASED:
                EVAL_SEMAPHORE.release()
                EVAL_SEMAPHORE_RELEASED.add(eval_run_id)
            run_data = ACTIVE_EVAL_RUNS.get(eval_run_id)
            if run_data:
                run_data["finished_at"] = time.time()
                for queue in list(run_data["listeners"]):
                    try:
                        queue.put_nowait(None)
                    except asyncio.QueueFull:
                        pass

    asyncio.create_task(run_eval_in_background())
    return {"eval_run_id": eval_run_id, "status": "running"}


@router.get("/evals/runs/{eval_run_id}/events")
async def get_eval_run_events(eval_run_id: str) -> StreamingResponse:
    require_harness_runtime()
    run_data = ACTIVE_EVAL_RUNS.get(eval_run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Eval run not found")

    async def event_generator():
        for event in list(run_data["events"]):
            yield f"data: {json.dumps(Sanitizer.sanitize_data(event))}\n\n"  # type: ignore[union-attr]

        if run_data["status"] != "running":
            return

        if len(run_data["listeners"]) >= 16:
            raise HTTPException(status_code=429, detail="Too many event listeners for this eval run")
        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=1024)
        run_data["listeners"].append(queue)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(Sanitizer.sanitize_data(event))}\n\n"  # type: ignore[union-attr]
        finally:
            if queue in run_data["listeners"]:
                run_data["listeners"].remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/evals/runs/{eval_run_id}")
async def get_eval_run(eval_run_id: str) -> dict[str, Any]:
    require_harness_runtime()
    run_data = ACTIVE_EVAL_RUNS.get(eval_run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Eval run not found")

    result = run_data["result"]
    sanitized_result = None
    if result is not None:
        sanitized_result = Sanitizer.sanitize_data(result.model_dump())  # type: ignore[union-attr]

    return {
        "eval_run_id": eval_run_id,
        "status": run_data["status"],
        "error": run_data["error"],
        "result": sanitized_result,
        "events": Sanitizer.sanitize_data(list(run_data["events"])),  # type: ignore[union-attr]
        "created_at": run_data.get("created_at"),
        "finished_at": run_data.get("finished_at"),
    }
