# Owner: Platform Operations
import uuid
from typing import Any, Dict, List, Optional

from app.db.session import get_db_session
from app.services.agents.connectors.audit import connector_audit
from app.services.agents.connectors.connector_token_rotation import TokenRotationService
from app.services.agents.connectors.credentials import credential_manager
from app.services.agents.connectors.oauth import OAuthService
from app.services.agents.connectors.registry import connector_registry
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/connectors", tags=["agent-connectors-admin"])

# OAuth Schemas
class OAuthClientCreate(BaseModel):
    client_id: str
    client_secret: str
    auth_url: str
    token_url: str
    redirect_uri: str

class OAuthStartRequest(BaseModel):
    connector_name: str

class OAuthCallbackRequest(BaseModel):
    code: str
    state: str

# Existing Schemas
class ConnectorResponse(BaseModel):
    name: str
    version: str
    provider: str
    capabilities: List[str]
    risk_level: str
    side_effect_level: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    required_scopes: List[str]

class ExecuteRequest(BaseModel):
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: str = "default"
    credential_id: Optional[str] = None

class DryRunRequest(BaseModel):
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: str = "default"

# Endpoints
@router.get("", response_model=List[ConnectorResponse])
async def list_connectors():
    """Lists all available SaaS connectors."""
    connectors = connector_registry.list_connectors()
    return [
        ConnectorResponse(
            name=c.connector_name,
            version=c.connector_version,
            provider=c.provider,
            capabilities=[cap.value for cap in c.capabilities],
            risk_level=c.risk_level.value,
            side_effect_level=c.side_effect_level.value,
            input_schema=c.input_schema,
            output_schema=c.output_schema,
            required_scopes=c.required_scopes
        )
        for c in connectors
    ]

@router.get("/{name}", response_model=ConnectorResponse)
async def get_connector(name: str):
    """Gets details for a specific connector."""
    connector = connector_registry.get_connector(name)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector {name} not found")
    
    return ConnectorResponse(
        name=connector.connector_name,
        version=connector.connector_version,
        provider=connector.provider,
        capabilities=[cap.value for cap in connector.capabilities],
        risk_level=connector.risk_level.value,
        side_effect_level=connector.side_effect_level.value,
        input_schema=connector.input_schema,
        output_schema=connector.output_schema,
        required_scopes=connector.required_scopes
    )

@router.post("/{name}/dry-run")
async def dry_run_connector(name: str, payload: DryRunRequest):
    """Performs a dry-run for a connector action."""
    connector = connector_registry.get_connector(name)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector {name} not found")
    
    credentials = credential_manager.get_credentials(payload.tenant_id, name)
    
    try:
        result = await connector.dry_run(
            tenant_id=payload.tenant_id,
            credentials=credentials,
            action=payload.action,
            params=payload.params
        )
        
        connector_audit.log_action(
            tenant_id=payload.tenant_id,
            connector_name=name,
            action=payload.action,
            request_params=payload.params,
            response=result,
            risk_level=connector.risk_level.value,
            is_dry_run=True
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{name}/execute")
async def execute_connector(name: str, payload: ExecuteRequest):
    """Executes a real action on a SaaS connector."""
    connector = connector_registry.get_connector(name)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector {name} not found")
    
    credentials = credential_manager.get_credentials(payload.tenant_id, name, payload.credential_id)
    if not credentials and name.upper() not in ["GITHUB", "SLACK", "JIRA", "CONFLUENCE", "SALESFORCE", "MICROSOFT365"]: # Simplified check
         raise HTTPException(status_code=401, detail="No credentials found for this connector")

    try:
        result = await connector.execute(
            tenant_id=payload.tenant_id,
            credentials=credentials,
            action=payload.action,
            params=payload.params
        )
        
        connector_audit.log_action(
            tenant_id=payload.tenant_id,
            connector_name=name,
            action=payload.action,
            request_params=payload.params,
            response=result,
            risk_level=connector.risk_level.value,
            is_dry_run=False
        )
        
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{name}/audit")
async def get_connector_audit(name: str, tenant_id: str = "default"):
    """
    Retrieves audit logs for a connector.
    In a real app, this would query a database.
    """
    return {"message": "Audit logs retrieval not fully implemented in this prototype", "connector": name}

@router.post("/{name}/oauth/clients")
async def register_oauth_client(name: str, payload: OAuthClientCreate, db: AsyncSession = Depends(get_db_session)):
    service = OAuthService(db)
    client = await service.register_client("default", name, payload.model_dump())
    return {"status": "success", "client_id": client.id}

@router.post("/{name}/oauth/start")
async def start_oauth_flow(name: str, db: AsyncSession = Depends(get_db_session)):
    service = OAuthService(db)
    return await service.start_flow("default", name)

@router.post("/{name}/oauth/callback")
async def oauth_callback(name: str, payload: OAuthCallbackRequest, db: AsyncSession = Depends(get_db_session)):
    service = OAuthService(db)
    return await service.handle_callback("default", name, payload.code, payload.state)

@router.post("/credentials/{id}/rotate")
async def rotate_credential(id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    service = TokenRotationService(db)
    new_token = await service.refresh_token_if_needed(id)
    if not new_token:
        raise HTTPException(status_code=400, detail="Credential cannot be rotated or is invalid")
    return {"status": "rotated"}

@router.delete("/credentials/{id}")
async def revoke_credential(id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    service = TokenRotationService(db)
    await service.revoke_token(id)
    return {"status": "revoked"}
