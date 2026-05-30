# Owner: agent-platform
import logging
import uuid
import httpx
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.agents import AgentDefinition, AgentA2ARegistration, AgentDelegationPolicy
from app.services.admin_rbac import record_admin_audit_event
from app.services.agents.a2a.a2a_security import A2ASecurityService
from app.services.agents.a2a.a2a_messages import A2AMessagePayload, A2ADelegationPayload

logger = logging.getLogger("a2a_client")

class A2AClientService:
    @staticmethod
    async def send_message(
        db: AsyncSession,
        tenant_id: str,
        sender_agent_id: uuid.UUID,
        recipient_agent_id: uuid.UUID,
        conversation_id: str,
        content_type: str,
        payload_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        A2ASecurityService.verify_a2a_enabled_or_raise()

        # 1. Fetch registrations
        stmt_sender = select(AgentA2ARegistration).where(
            AgentA2ARegistration.agent_id == sender_agent_id,
            AgentA2ARegistration.tenant_id == tenant_id
        )
        res_sender = await db.execute(stmt_sender)
        sender_reg = res_sender.scalar_one_or_none()
        if not sender_reg:
            raise HTTPException(status_code=404, detail=f"Sender agent {sender_agent_id} registration not found.")

        stmt_recipient = select(AgentA2ARegistration).where(
            AgentA2ARegistration.agent_id == recipient_agent_id,
            AgentA2ARegistration.tenant_id == tenant_id
        )
        res_recipient = await db.execute(stmt_recipient)
        recipient_reg = res_recipient.scalar_one_or_none()
        if not recipient_reg:
            raise HTTPException(status_code=404, detail=f"Recipient agent {recipient_agent_id} registration not found.")

        # Tenant isolation check
        if sender_reg.tenant_id != tenant_id or recipient_reg.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Cross-tenant communication is strictly blocked.")

        # Create message payload
        msg_payload = A2AMessagePayload(
            conversation_id=conversation_id,
            sender_agent_id=str(sender_agent_id),
            recipient_agent_id=str(recipient_agent_id),
            content_type=content_type,
            payload=payload_data
        )

        # Sign payload using sender's auth_token
        payload_dict = msg_payload.model_dump()
        # Convert timestamp to string for json serialization consistency in signing
        payload_dict["timestamp"] = payload_dict["timestamp"].isoformat()
        signature = A2ASecurityService.generate_signature(payload_dict, sender_reg.auth_token)
        payload_dict["signature"] = signature

        # Deliver message
        response_data = {"status": "dispatched", "message_id": payload_dict["message_id"]}
        if recipient_reg.target_url and not recipient_reg.target_url.startswith("mock://") and not recipient_reg.target_url.startswith("internal://"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    headers = {"X-Agent-A2A-Token": sender_reg.auth_token}
                    endpoint = f"{recipient_reg.target_url.rstrip('/')}/agents/a2a/message"
                    resp = await client.post(endpoint, json=payload_dict, headers=headers)
                    if resp.status_code >= 400:
                        raise HTTPException(
                            status_code=resp.status_code,
                            detail=f"Failed to deliver message via HTTP to external agent: {resp.text}"
                        )
                    response_data["http_response"] = resp.json()
            except httpx.RequestError as exc:
                logger.error(f"HTTP request failed delivering A2A message to {recipient_reg.target_url}: {exc}")
                raise HTTPException(status_code=502, detail=f"Network error communicating with external agent: {exc}")
        else:
            # Local/mock delivery simulation
            response_data["status"] = "delivered_locally"

        # Record audit event
        await record_admin_audit_event(
            db,
            event_type="agent.a2a.message.sent",
            status="success",
            actor_identifier=str(sender_agent_id),
            target_type="agent",
            target_id=str(recipient_agent_id),
            metadata={
                "message_id": payload_dict["message_id"],
                "conversation_id": conversation_id,
                "tenant_id": tenant_id,
                "delivery_mode": response_data["status"]
            }
        )

        return response_data

    @staticmethod
    async def delegate_task(
        db: AsyncSession,
        tenant_id: str,
        delegator_agent_id: uuid.UUID,
        delegatee_agent_id: uuid.UUID,
        task_description: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        A2ASecurityService.verify_a2a_enabled_or_raise()

        # 1. Fetch registrations
        stmt_delegator = select(AgentA2ARegistration).where(
            AgentA2ARegistration.agent_id == delegator_agent_id,
            AgentA2ARegistration.tenant_id == tenant_id
        )
        res_delegator = await db.execute(stmt_delegator)
        delegator_reg = res_delegator.scalar_one_or_none()
        if not delegator_reg:
            raise HTTPException(status_code=404, detail=f"Delegator agent {delegator_agent_id} registration not found.")

        stmt_delegatee = select(AgentA2ARegistration).where(
            AgentA2ARegistration.agent_id == delegatee_agent_id,
            AgentA2ARegistration.tenant_id == tenant_id
        )
        res_delegatee = await db.execute(stmt_delegatee)
        delegatee_reg = res_delegatee.scalar_one_or_none()
        if not delegatee_reg:
            raise HTTPException(status_code=404, detail=f"Delegatee agent {delegatee_agent_id} registration not found.")

        # Tenant isolation check
        if delegator_reg.tenant_id != tenant_id or delegatee_reg.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Cross-tenant delegation is strictly blocked.")

        # 2. Check Delegation Policy
        stmt_policy = select(AgentDelegationPolicy).where(
            AgentDelegationPolicy.source_agent_id == delegator_agent_id,
            AgentDelegationPolicy.target_agent_id == delegatee_agent_id,
            AgentDelegationPolicy.tenant_id == tenant_id,
            AgentDelegationPolicy.is_active == True
        )
        res_policy = await db.execute(stmt_policy)
        policy = res_policy.scalar_one_or_none()
        if not policy:
            raise HTTPException(
                status_code=403,
                detail=f"Delegation policy from {delegator_agent_id} to {delegatee_agent_id} does not exist or is inactive."
            )

        # Create delegation payload
        delegation_payload = A2ADelegationPayload(
            delegator_agent_id=str(delegator_agent_id),
            delegatee_agent_id=str(delegatee_agent_id),
            task_description=task_description,
            input_data=input_data
        )

        # Sign payload using delegator's auth_token
        payload_dict = delegation_payload.model_dump()
        # Convert timestamp to string for json serialization consistency in signing
        payload_dict["timestamp"] = payload_dict["timestamp"].isoformat()
        signature = A2ASecurityService.generate_signature(payload_dict, delegator_reg.auth_token)
        payload_dict["signature"] = signature

        # Deliver delegation request
        response_data = {"status": "delegated", "task_id": payload_dict["task_id"]}
        if delegatee_reg.target_url and not delegatee_reg.target_url.startswith("mock://") and not delegatee_reg.target_url.startswith("internal://"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    headers = {"X-Agent-A2A-Token": delegator_reg.auth_token}
                    endpoint = f"{delegatee_reg.target_url.rstrip('/')}/agents/a2a/delegate"
                    resp = await client.post(endpoint, json=payload_dict, headers=headers)
                    if resp.status_code >= 400:
                        raise HTTPException(
                            status_code=resp.status_code,
                            detail=f"Failed to delegate task via HTTP to external agent: {resp.text}"
                        )
                    response_data["http_response"] = resp.json()
            except httpx.RequestError as exc:
                logger.error(f"HTTP request failed delegating task to {delegatee_reg.target_url}: {exc}")
                raise HTTPException(status_code=502, detail=f"Network error communicating with external agent: {exc}")
        else:
            # Local/mock delegation simulation
            response_data["status"] = "delegated_locally"

        # Record audit event
        await record_admin_audit_event(
            db,
            event_type="agent.a2a.delegation.sent",
            status="success",
            actor_identifier=str(delegator_agent_id),
            target_type="agent",
            target_id=str(delegatee_agent_id),
            metadata={
                "task_id": payload_dict["task_id"],
                "tenant_id": tenant_id,
                "delivery_mode": response_data["status"]
            }
        )

        return response_data
