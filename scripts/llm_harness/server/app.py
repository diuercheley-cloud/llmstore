# scripts/llm_harness/server/app.py
import asyncio
import contextlib
import hmac
import json
import logging
import os
import time
import uuid
from collections import defaultdict
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from ..config import HarnessConfig
from ..evals.loader import EvalLoader
from ..evals.runner import EvalRunner
from ..legacy_runner import run_harness
from ..providers import _PROVIDER_REGISTRY
from ..sanitizer import Sanitizer

logger = logging.getLogger("llm_harness.server")

# In-memory stores for runs and eval runs
ACTIVE_RUNS: Dict[str, Dict[str, Any]] = {}
ACTIVE_EVAL_RUNS: Dict[str, Dict[str, Any]] = {}

# Concurrency control
MAX_CONCURRENT_RUNS = 10
_run_semaphore = asyncio.Semaphore(MAX_CONCURRENT_RUNS)

# Rate limiting: sliding window per client IP
RATE_LIMIT_WINDOW = 60.0
RATE_LIMIT_MAX_REQUESTS = 30
_rate_limit_store: Dict[str, List[float]] = defaultdict(list)

class ServerConfig:
    api_key_env: Optional[str] = None
    allow_stub: bool = True
    rate_limit_enabled: bool = True

server_config = ServerConfig()


def _check_rate_limit(client_ip: str) -> Tuple[bool, int]:
    if not server_config.rate_limit_enabled:
        return True, 0
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW
    timestamps = _rate_limit_store[client_ip]
    timestamps[:] = [t for t in timestamps if t > window_start]
    if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        retry_after = int(timestamps[0] + RATE_LIMIT_WINDOW - now) + 1
        return False, retry_after
    timestamps.append(now)
    return True, 0


def get_api_key() -> Optional[str]:
    if server_config.api_key_env:
        return os.getenv(server_config.api_key_env)
    return None


def verify_auth(authorization: Optional[str] = Header(None)):
    expected_key = get_api_key()
    if not expected_key:
        return
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    if not hmac.compare_digest(parts[1], expected_key):
        raise HTTPException(status_code=401, detail="Invalid API Key")


async def _rate_limit_cleanup_loop():
    while True:
        await asyncio.sleep(300)
        now = time.monotonic()
        cutoff = now - RATE_LIMIT_WINDOW
        for ip in list(_rate_limit_store.keys()):
            _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if t > cutoff]
            if not _rate_limit_store[ip]:
                del _rate_limit_store[ip]


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    task = asyncio.create_task(_rate_limit_cleanup_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="LLM Harness Server API", lifespan=lifespan)


class RunRequest(BaseModel):
    task: str
    agent_id: Optional[str] = "default-coder"
    workspace: Optional[str] = None
    provider: Optional[str] = "stub"
    model: Optional[str] = ""
    config_overrides: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("task")
    @classmethod
    def task_size_limit(cls, v: str) -> str:
        if len(v) > 100_000:
            raise ValueError("task exceeds maximum length of 100,000 characters")
        return v


class EvalRunRequest(BaseModel):
    suite_path: str
    concurrency: int = 1
    provider: Optional[str] = "stub"
    model: Optional[str] = ""
    config_overrides: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("suite_path")
    @classmethod
    def suite_path_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("suite_path must not be empty")
        return v

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = _check_rate_limit(client_ip)
    if not allowed:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(retry_after)},
        )
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/runs", dependencies=[Depends(verify_auth)])
async def create_run(req: RunRequest, background_tasks: BackgroundTasks):
    acquired = await _run_semaphore.acquire()
    if not acquired:
        raise HTTPException(status_code=503, detail="Server busy, too many concurrent runs")

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
    }

    def progress_callback(event: Dict[str, Any]):
        if run_id in ACTIVE_RUNS:
            ACTIVE_RUNS[run_id]["events"].append(event)
            for q in ACTIVE_RUNS[run_id]["listeners"]:
                q.put_nowait(event)

    config_overrides = {
        "code_agent": req.agent_id,
        "provider": req.provider,
        "model": req.model,
        **req.config_overrides,
    }

    async def run_loop_bg():
        try:
            result = await run_harness(
                task=req.task,
                progress_callback=progress_callback,
                workspace_path=req.workspace,
                allow_stub=server_config.allow_stub,
                config=HarnessConfig(**config_overrides),
            )
            if run_id in ACTIVE_RUNS:
                ACTIVE_RUNS[run_id]["status"] = "completed" if result.success else "failed"
                ACTIVE_RUNS[run_id]["result"] = result
        except asyncio.CancelledError:
            if run_id in ACTIVE_RUNS:
                ACTIVE_RUNS[run_id]["status"] = "cancelled"
            raise
        except Exception as e:
            logger.exception("Error running harness in server mode")
            if run_id in ACTIVE_RUNS:
                ACTIVE_RUNS[run_id]["status"] = "failed"
                ACTIVE_RUNS[run_id]["error"] = str(e)
        finally:
            _run_semaphore.release()
            if run_id in ACTIVE_RUNS:
                for q in ACTIVE_RUNS[run_id]["listeners"]:
                    q.put_nowait(None)

    task_handle = asyncio.create_task(run_loop_bg())
    ACTIVE_RUNS[run_id]["task_handle"] = task_handle

    return {"run_id": run_id, "status": "running"}

@app.get("/runs/{run_id}", dependencies=[Depends(verify_auth)])
def get_run(run_id: str):
    if run_id not in ACTIVE_RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run_data = ACTIVE_RUNS[run_id]
    result_dump = None
    if run_data["result"] is not None:
        result_dump = Sanitizer.sanitize_data(run_data["result"].model_dump())

    return {
        "run_id": run_id,
        "task": run_data["task"],
        "status": run_data["status"],
        "error": run_data["error"],
        "result": result_dump,
    }

@app.get("/runs/{run_id}/events", dependencies=[Depends(verify_auth)])
async def get_run_events(run_id: str):
    if run_id not in ACTIVE_RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    run_data = ACTIVE_RUNS[run_id]

    async def event_generator():
        # First send any existing events
        for event in list(run_data["events"]):
            yield f"data: {json.dumps(Sanitizer.sanitize_data(event))}\n\n"

        if run_data["status"] == "running":
            q: asyncio.Queue[Any] = asyncio.Queue()
            run_data["listeners"].append(q)
            try:
                while True:
                    event = await q.get()
                    if event is None:
                        break
                    yield f"data: {json.dumps(Sanitizer.sanitize_data(event))}\n\n"
            finally:
                if q in run_data["listeners"]:
                    run_data["listeners"].remove(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/runs/{run_id}/cancel", dependencies=[Depends(verify_auth)])
def cancel_run(run_id: str):
    if run_id not in ACTIVE_RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run_data = ACTIVE_RUNS[run_id]
    if run_data["status"] == "running" and run_data["task_handle"]:
        run_data["task_handle"].cancel()
        run_data["status"] = "cancelled"
        # Notify queue listeners of EOF
        for q in run_data["listeners"]:
            q.put_nowait(None)
        return {"status": "cancelled"}
    return {"status": run_data["status"]}

@app.get("/providers", dependencies=[Depends(verify_auth)])
def get_providers():
    # Return sanitized registry keys
    return {"providers": sorted(list(_PROVIDER_REGISTRY.keys()))}

@app.get("/tools", dependencies=[Depends(verify_auth)])
def get_tools():
    # Return basic list of registered tools
    core_tools = [
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
    # In the future, dynamically add plugin/mcp tools here if registered.
    from ..plugins import plugin_registry
    for name, tool_class in plugin_registry.list_tools().items():
        core_tools.append({"name": name, "description": f"Plugin tool: {tool_class.__name__}"})
    
    from ..mcp import mcp_client
    if mcp_client.is_enabled():
        for name, tool in mcp_client.list_tools().items():
            core_tools.append({
                "name": f"mcp:{name}",
                "description": tool.get("description", "MCP Tool"),
            })
            
    return {"tools": core_tools}

@app.get("/evals", dependencies=[Depends(verify_auth)])
def get_evals():
    evals_dir = "examples/llm_harness/evals"
    files = []
    if os.path.exists(evals_dir):
        for f in os.listdir(evals_dir):
            if f.endswith(".eval_suite.json") or f.endswith(".eval_suite.yaml"):
                files.append(f)
    return {"eval_suites": sorted(files)}

@app.post("/evals/run", dependencies=[Depends(verify_auth)])
async def run_evals(req: EvalRunRequest):
    eval_run_id = str(uuid.uuid4())
    ACTIVE_EVAL_RUNS[eval_run_id] = {
        "eval_run_id": eval_run_id,
        "status": "running",
        "result": None,
        "error": None,
    }

    async def run_eval_bg():
        try:
            suite = EvalLoader.load(req.suite_path)
            provider = req.provider or "stub"
            model = req.model or ""
            eval_kwargs: Dict[str, Any] = {
                "suite": suite,
                "provider": provider,
                "model": model,
                "allow_stub": server_config.allow_stub,
            }
            for k, v in req.config_overrides.items():
                eval_kwargs[k] = v

            runner = EvalRunner(**eval_kwargs)
            result = await runner.run_all(concurrency=req.concurrency)
            if eval_run_id in ACTIVE_EVAL_RUNS:
                ACTIVE_EVAL_RUNS[eval_run_id]["status"] = "completed"
                ACTIVE_EVAL_RUNS[eval_run_id]["result"] = result
        except Exception as e:
            logger.exception("Error running evals in server mode")
            if eval_run_id in ACTIVE_EVAL_RUNS:
                ACTIVE_EVAL_RUNS[eval_run_id]["status"] = "failed"
                ACTIVE_EVAL_RUNS[eval_run_id]["error"] = str(e)

    asyncio.create_task(run_eval_bg())
    return {"eval_run_id": eval_run_id, "status": "running"}

@app.get("/evals/{eval_run_id}", dependencies=[Depends(verify_auth)])
def get_eval_run_status(eval_run_id: str):
    if eval_run_id not in ACTIVE_EVAL_RUNS:
        raise HTTPException(status_code=404, detail="Eval run not found")
    
    run_data = ACTIVE_EVAL_RUNS[eval_run_id]
    result_dump = None
    if run_data["result"] is not None:
        result_dump = Sanitizer.sanitize_data(run_data["result"].model_dump())
        
    return {
        "eval_run_id": eval_run_id,
        "status": run_data["status"],
        "error": run_data["error"],
        "result": result_dump,
    }


@app.post("/shutdown", dependencies=[Depends(verify_auth)])
async def shutdown_server():
    logger.info("Shutdown requested, cancelling active runs...")
    for run_id, run_data in list(ACTIVE_RUNS.items()):
        if run_data["status"] == "running" and run_data.get("task_handle"):
            run_data["task_handle"].cancel()
            run_data["status"] = "cancelled"
            for q in run_data["listeners"]:
                q.put_nowait(None)
    for eval_run_id, eval_data in list(ACTIVE_EVAL_RUNS.items()):
        if eval_data["status"] == "running":
            eval_data["status"] = "shutdown"
    ACTIVE_RUNS.clear()
    ACTIVE_EVAL_RUNS.clear()
    _rate_limit_store.clear()
    logger.info("Server shutdown complete")
    return {"status": "shutdown"}
