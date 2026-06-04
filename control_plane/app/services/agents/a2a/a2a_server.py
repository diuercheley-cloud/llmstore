# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict

from app.models.agents import AgentA2ARegistration, AgentDelegationPolicy
from app.services.admin_rbac import record_admin_audit_event
from app.services.agents.a2a.a2a_security import A2ASecurityService
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("a2a_server")

class A2AServerService:
    @staticmethod
    async def receive_message(
        db: AsyncSession,
        message_payload: Dict[str, Any],
        token: str
    ) -> Dict[str, Any]:
        A2ASecurityService.verify_a2a_enabled_or_raise()

        # 1. Authenticate sender agent via token
        sender_reg = await A2ASecurityService.authenticate_agent(db, token)
        
        # 2. Verify payload signature
        signature = message_payload.get("signature")
        if not signature:
            raise HTTPException(status_code=400, detail="Missing message signature.")
        
        if not A2ASecurityService.verify_signature(message_payload, sender_reg.auth_token, signature):
            raise HTTPException(status_code=400, detail="Invalid message signature.")

        # 3. Verify tenant safety & Recipient Registration
        recipient_id_str = message_payload.get("recipient_agent_id")
        if not recipient_id_str:
            raise HTTPException(status_code=400, detail="Missing recipient agent ID.")

        try:
            recipient_uuid = uuid.UUID(recipient_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid recipient agent ID format.")

        stmt_recipient = select(AgentA2ARegistration).where(
            AgentA2ARegistration.agent_id == recipient_uuid,
            AgentA2ARegistration.tenant_id == sender_reg.tenant_id
        )
        res_recipient = await db.execute(stmt_recipient)
        recipient_reg = res_recipient.scalar_one_or_none()
        if not recipient_reg:
            raise HTTPException(
                status_code=403,
                detail="Recipient agent is not registered or belongs to a different tenant."
            )

        # Record incoming message audit event
        await record_admin_audit_event(
            db,
            event_type="agent.a2a.message.received",
            status="success",
            actor_identifier=message_payload.get("sender_agent_id"),
            target_type="agent",
            target_id=recipient_id_str,
            metadata={
                "message_id": message_payload.get("message_id"),
                "conversation_id": message_payload.get("conversation_id"),
                "tenant_id": sender_reg.tenant_id
            }
        )

        return {"status": "success", "message_id": message_payload.get("message_id")}

    @staticmethod
    async def receive_delegation(
        db: AsyncSession,
        delegation_payload: Dict[str, Any],
        token: str
    ) -> Dict[str, Any]:
        A2ASecurityService.verify_a2a_enabled_or_raise()

        # 1. Authenticate sender agent via token
        sender_reg = await A2ASecurityService.authenticate_agent(db, token)

        # 2. Verify payload signature
        signature = delegation_payload.get("signature")
        if not signature:
            raise HTTPException(status_code=400, detail="Missing delegation signature.")

        if not A2ASecurityService.verify_signature(delegation_payload, sender_reg.auth_token, signature):
            raise HTTPException(status_code=400, detail="Invalid delegation signature.")

        # 3. Verify tenant safety & Delegatee registration
        delegatee_id_str = delegation_payload.get("delegatee_agent_id")
        delegator_id_str = delegation_payload.get("delegator_agent_id")
        if not delegatee_id_str or not delegator_id_str:
            raise HTTPException(status_code=400, detail="Missing delegator/delegatee agent ID.")

        try:
            delegatee_uuid = uuid.UUID(delegatee_id_str)
            delegator_uuid = uuid.UUID(delegator_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid agent ID format.")

        # Check delegatee (must be registered on same tenant)
        stmt_delegatee = select(AgentA2ARegistration).where(
            AgentA2ARegistration.agent_id == delegatee_uuid,
            AgentA2ARegistration.tenant_id == sender_reg.tenant_id
        )
        res_delegatee = await db.execute(stmt_delegatee)
        delegatee_reg = res_delegatee.scalar_one_or_none()
        if not delegatee_reg:
            raise HTTPException(
                status_code=403,
                detail="Delegatee agent is not registered or belongs to a different tenant."
            )

        # 4. Policy Check
        stmt_policy = select(AgentDelegationPolicy).where(
            AgentDelegationPolicy.source_agent_id == delegator_uuid,
            AgentDelegationPolicy.target_agent_id == delegatee_uuid,
            AgentDelegationPolicy.tenant_id == sender_reg.tenant_id,
            AgentDelegationPolicy.is_active == True
        )
        res_policy = await db.execute(stmt_policy)
        policy = res_policy.scalar_one_or_none()
        if not policy:
            raise HTTPException(
                status_code=403,
                detail=f"Delegation policy from {delegator_uuid} to {delegatee_uuid} does not exist or is inactive."
            )

        # Record incoming delegation audit event
        await record_admin_audit_event(
            db,
            event_type="agent.a2a.delegation.received",
            status="success",
            actor_identifier=delegator_id_str,
            target_type="agent",
            target_id=delegatee_id_str,
            metadata={
                "task_id": delegation_payload.get("task_id"),
                "tenant_id": sender_reg.tenant_id
            }
        )

        return {"status": "success", "task_id": delegation_payload.get("task_id")}
