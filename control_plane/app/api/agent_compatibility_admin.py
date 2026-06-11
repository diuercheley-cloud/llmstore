# Owner: platform-operations
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.dependencies import get_db, get_current_admin
from app.compat.report import CompatibilityAnalyzer
from app.compat.langgraph.importers import import_langgraph_from_source
from app.compat.langgraph.converters import convert_langgraph_to_workflow
from app.compat.crewai.importers import import_crew_from_source
from app.compat.crewai.converters import convert_crew_to_workflow
from app.compat.autogen.importers import import_autogen_agent_from_source
from app.compat.autogen.converters import convert_autogen_agent_to_agent_definition

router = APIRouter(prefix="/admin/compat", tags=["agent-compatibility-admin"])

class AnalyzeRequest(BaseModel):
    framework: str
    source_code: str

class MigrateRequest(BaseModel):
    framework: str
    source_code: str
    tenant_id: str
    name: str
    version: str
    description: Optional[str] = None

@router.post("/analyze")
async def analyze_compatibility(req: AnalyzeRequest):
    """
    Analyzes external agent source code and returns a CompatibilityReport.
    """
    try:
        report = CompatibilityAnalyzer.analyze_source_code(req.framework, req.source_code)
        return report.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Analysis failed: {str(e)}")

@router.post("/migrate")
async def migrate_agent(req: MigrateRequest, db: AsyncSession = Depends(get_db)):
    """
    Migrates external agent configurations (LangGraph, CrewAI, AutoGen) to native DB models.
    """
    framework = req.framework.lower()
    try:
        if framework == "langgraph":
            graph = import_langgraph_from_source(req.source_code)
            workflow_def = await convert_langgraph_to_workflow(
                db=db,
                tenant_id=req.tenant_id,
                name=req.name,
                version=req.version,
                graph=graph,
                description=req.description
            )
            await db.commit()
            return {
                "status": "success",
                "framework": framework,
                "workflow_definition_id": str(workflow_def.id),
                "nodes_count": len(workflow_def.nodes),
                "edges_count": len(workflow_def.edges)
            }
        elif framework == "crewai":
            crew = import_crew_from_source(req.source_code)
            workflow_def = await convert_crew_to_workflow(
                db=db,
                tenant_id=req.tenant_id,
                name=req.name,
                version=req.version,
                crew=crew,
                description=req.description
            )
            await db.commit()
            return {
                "status": "success",
                "framework": framework,
                "workflow_definition_id": str(workflow_def.id),
                "nodes_count": len(workflow_def.nodes),
                "edges_count": len(workflow_def.edges)
            }
        elif framework == "autogen":
            agent = import_autogen_agent_from_source(req.source_code)
            agent_def = await convert_autogen_agent_to_agent_definition(
                db=db,
                tenant_id=req.tenant_id,
                agent=agent
            )
            await db.commit()
            return {
                "status": "success",
                "framework": framework,
                "agent_definition_id": str(agent_def.id),
                "name": agent_def.name,
                "model_id": agent_def.model_id
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported framework: {framework}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Migration failed: {str(e)}")
