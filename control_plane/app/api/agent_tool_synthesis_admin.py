# Owner: agent-platform
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings, Settings
from app.api.deps import require_admin
from app.models.agent_tool_synthesis import (
    AgentGeneratedTool,
    AgentGeneratedToolVersion,
    AgentSandboxSession,
    AgentSandboxArtifact,
    AgentCodeInterpreterRun
)
from app.services.agents.tool_synthesis import (
    ToolSynthesizer,
    GeneratedToolSchema,
    GeneratedToolRegistry,
    validate_generated_code,
    SandboxRuntime,
    CodeInterpreter,
    SandboxPolicy,
    SandboxArtifacts
)
from pydantic import BaseModel

admin_router = APIRouter(prefix="/admin/agents/tool-synthesis", tags=["agent-tool-synthesis"])
sandbox_router = APIRouter(prefix="/admin/agents/sandbox", tags=["agent-sandbox"])
public_router = APIRouter(prefix="/agents/tools/generated", tags=["agent-generated-tools"])

class GenerateToolRequest(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    prompt: str
    agent_id: uuid.UUID | None = None

class ValidateToolRequest(BaseModel):
    code: str

class TestToolRequest(BaseModel):
    code: str
    timeout_seconds: int = 5

class ApproveToolRequest(BaseModel):
    approver: str

class ExecuteToolRequest(BaseModel):
    parameters: Dict[str, Any]
    timeout_seconds: int = 5


@admin_router.post("/generate")
def generate_tool(req: GenerateToolRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings), _: dict = Depends(require_admin)):
    if not settings.agent_tool_synthesis_enabled:
        raise HTTPException(status_code=400, detail="Tool synthesis is not enabled")
    
    synthesizer = ToolSynthesizer()
    schema = GeneratedToolSchema(name=req.name, description=req.description, parameters=req.parameters)
    code = synthesizer.generate_tool_code(schema, req.prompt)
    
    registry = GeneratedToolRegistry(db)
    tool = registry.register_tool(name=req.name, description=req.description, author_id=req.agent_id)
    version = registry.add_tool_version(tool_id=tool.id, version_tag="v1", code=code, schema_json=req.parameters)
    
    return {"tool_id": str(tool.id), "version_id": str(version.id), "code": code}

@admin_router.post("/{version_id}/validate")
def validate_tool(version_id: uuid.UUID, req: ValidateToolRequest, settings: Settings = Depends(get_settings), _: dict = Depends(require_admin)):
    if not settings.agent_tool_synthesis_enabled:
        raise HTTPException(status_code=400, detail="Tool synthesis is not enabled")
    
    try:
        validate_generated_code(req.code, allow_network=settings.agent_code_sandbox_network_enabled, allow_write=settings.agent_code_sandbox_write_enabled)
        return {"status": "valid"}
    except Exception as e:
        return {"status": "invalid", "error": str(e)}

@admin_router.post("/{version_id}/test")
def test_tool(version_id: uuid.UUID, req: TestToolRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings), _: dict = Depends(require_admin)):
    if not settings.agent_code_interpreter_enabled:
        raise HTTPException(status_code=400, detail="Code interpreter is not enabled")
    
    interpreter = CodeInterpreter(db, allow_network=settings.agent_code_sandbox_network_enabled, allow_write=settings.agent_code_sandbox_write_enabled)
    session = interpreter.create_session(ttl_seconds=300)
    
    run = interpreter.run_code(session_id=session.id, code=req.code, timeout_seconds=req.timeout_seconds)
    
    return {
        "run_id": str(run.id),
        "stdout": run.stdout,
        "stderr": run.stderr,
        "exit_code": run.exit_code,
        "execution_time_ms": run.execution_time_ms
    }

@admin_router.post("/{version_id}/approve")
def approve_tool(version_id: uuid.UUID, req: ApproveToolRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings), _: dict = Depends(require_admin)):
    if not settings.agent_tool_synthesis_enabled:
        raise HTTPException(status_code=400, detail="Tool synthesis is not enabled")
    
    registry = GeneratedToolRegistry(db)
    version = registry.approve_version(version_id=version_id, approver=req.approver)
    if not version:
        raise HTTPException(status_code=404, detail="Tool version not found")
        
    return {"status": "approved", "version_id": str(version.id)}

@sandbox_router.get("/sessions")
def list_sandbox_sessions(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    sessions = db.query(AgentSandboxSession).limit(100).all()
    return [{"id": str(s.id), "status": s.status, "created_at": s.created_at} for s in sessions]

@sandbox_router.get("/artifacts/{artifact_id}")
def get_sandbox_artifact(artifact_id: uuid.UUID, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    artifact = db.query(AgentSandboxArtifact).filter(AgentSandboxArtifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"id": str(artifact.id), "filename": artifact.filename, "size_bytes": artifact.size_bytes}


@public_router.post("/{tool_id}/execute")
def execute_generated_tool(tool_id: uuid.UUID, req: ExecuteToolRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    if not settings.agent_dynamic_tool_execution_enabled:
        raise HTTPException(status_code=400, detail="Dynamic tool execution is not enabled")
        
    registry = GeneratedToolRegistry(db)
    tool = registry.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
        
    # Get the latest version or approved version
    version = None
    for v in tool.versions:
        if v.is_approved:
            version = v
            break
            
    if not version:
        raise HTTPException(status_code=400, detail="No approved version available for this tool")
        
    interpreter = CodeInterpreter(db, allow_network=settings.agent_code_sandbox_network_enabled, allow_write=settings.agent_code_sandbox_write_enabled)
    session = interpreter.create_session(ttl_seconds=300)
    
    # We create a small script that calls the function with provided parameters
    code = version.code + "\n"
    # Basic parameter mapping mock
    params_str = ", ".join([f"{k}={repr(v)}" for k, v in req.parameters.items()])
    code += f"result = {tool.name}({params_str})\nprint(result)\n"
    
    run = interpreter.run_code(session_id=session.id, code=code, timeout_seconds=req.timeout_seconds)
    
    return {
        "run_id": str(run.id),
        "stdout": run.stdout,
        "stderr": run.stderr,
        "exit_code": run.exit_code
    }
