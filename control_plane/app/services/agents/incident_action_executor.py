# Owner: agent-platform
import logging
import uuid
from typing import Any

from app.core.time import utc_now
from app.domains.auth.repositories import SqlAlchemyAuthRepository
from app.models.agents.agents import (
    AgentApprovalRequest,
    AgentDefinition,
    AgentMemoryQuarantine,
    AgentQueueThrottle,
    AgentRun,
    AgentTool,
)
from app.services.admin_rbac import is_rbac_admin_enabled, record_admin_audit_event
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class IncidentActionExecutor:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _validate_permission(self, performed_by: str) -> None:
        """
        Validate that the performed_by user has appropriate governance permissions.
        If RBAC is enabled, verifies 'governance:write' or 'superadmin:all'.
        If RBAC is disabled, allows standard admin identifiers.
        """
        if is_rbac_admin_enabled():
            repo = SqlAlchemyAuthRepository(self.db)
            user_data = await repo.get_user_by_username(performed_by)
            if not user_data:
                # Try loading by ID if it's a UUID string
                try:
                    uuid.UUID(performed_by)
                    user_data = await repo.get_user_by_id(performed_by)
                except ValueError:
                    pass

            if not user_data:
                raise ValueError(f"User {performed_by} not found or unauthorized")

            permissions = set(user_data.permissions)
            roles = set(user_data.roles)
            is_super = "superadmin:all" in permissions or "superadmin" in roles
            if not (is_super or "governance:write" in permissions):
                raise ValueError(
                    f"User {performed_by} does not have required 'governance:write' permission"
                )
        else:
            allowed_roles = {
                "admin_write",
                "super_admin",
                "admin",
                "legacy-bootstrap-admin",
                "superadmin",
            }
            if performed_by not in allowed_roles:
                # Allow username lookups as a fallback to see if they exist in the DB
                repo = SqlAlchemyAuthRepository(self.db)
                user_data = await repo.get_user_by_username(performed_by)
                if user_data:
                    roles = set(user_data.roles)
                    permissions = set(user_data.permissions)
                    if not (
                        roles.intersection(allowed_roles)
                        or "governance:write" in permissions
                        or "superadmin:all" in permissions
                    ):
                        raise ValueError(f"User {performed_by} does not have required permissions")
                else:
                    raise ValueError(f"User {performed_by} does not have permission")

    async def disable_tool(
        self,
        tool_id: str,
        scope: str | None = None,
        performed_by: str = "system",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Disables an AgentTool by setting enabled = False.
        """
        await self._validate_permission(performed_by)

        # Look up tool by ID or by Name
        tool_uuid = None
        try:
            tool_uuid = uuid.UUID(tool_id)
        except ValueError:
            pass

        if tool_uuid:
            stmt = select(AgentTool).where(AgentTool.id == tool_uuid)
        else:
            stmt = select(AgentTool).where(AgentTool.name == tool_id)

        res = await self.db.execute(stmt)
        tool = res.scalar_one_or_none()
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        if scope and tool.scope != scope:
            raise ValueError(f"Tool scope mismatch: expected {scope}, found {tool.scope}")

        previous_state = tool.enabled

        if not previous_state:
            # Already disabled - idempotent
            return {
                "action": "disable_tool",
                "tool_id": str(tool.id),
                "tool_name": tool.name,
                "scope": tool.scope,
                "previous_state": False,
                "current_state": False,
                "dry_run": dry_run,
                "changed": False,
                "rollback_data": {
                    "tool_id": str(tool.id),
                    "previous_state": False,
                },
            }

        if not dry_run:
            tool.enabled = False
            self.db.add(tool)
            await self.db.commit()

        await record_admin_audit_event(
            self.db,
            event_type="agent.containment.disable_tool",
            status="success" if not dry_run else "dry_run",
            actor_identifier=performed_by,
            target_type="agent_tool",
            target_id=str(tool.id),
            metadata={
                "tool_name": tool.name,
                "scope": tool.scope,
                "dry_run": dry_run,
            },
        )

        return {
            "action": "disable_tool",
            "tool_id": str(tool.id),
            "tool_name": tool.name,
            "scope": tool.scope,
            "previous_state": previous_state,
            "current_state": False if not dry_run else previous_state,
            "dry_run": dry_run,
            "changed": not dry_run,
            "rollback_data": {
                "tool_id": str(tool.id),
                "previous_state": previous_state,
            },
        }

    async def quarantine_memory(
        self,
        target_id: str,
        reason: str | None = None,
        performed_by: str = "system",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Puts agent memory or a specific memory/collection in quarantine.
        """
        await self._validate_permission(performed_by)

        # Detect target type: Check if target_id corresponds to an AgentDefinition UUID
        target_type = "memory"
        try:
            target_uuid = uuid.UUID(target_id)
            agent = await self.db.get(AgentDefinition, target_uuid)
            if agent:
                target_type = "agent"
        except ValueError:
            pass

        # Idempotency check: Check if already quarantined
        stmt = select(AgentMemoryQuarantine).where(AgentMemoryQuarantine.target_id == target_id)
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            return {
                "action": "quarantine_memory",
                "target_id": target_id,
                "target_type": existing.target_type,
                "reason": existing.reason,
                "dry_run": dry_run,
                "changed": False,
                "rollback_data": {
                    "target_id": target_id,
                },
            }

        if not dry_run:
            quarantine = AgentMemoryQuarantine(
                target_id=target_id,
                target_type=target_type,
                reason=reason,
                quarantined_by=performed_by,
                created_at=utc_now(),
            )
            self.db.add(quarantine)
            await self.db.commit()

        await record_admin_audit_event(
            self.db,
            event_type="agent.containment.quarantine_memory",
            status="success" if not dry_run else "dry_run",
            actor_identifier=performed_by,
            target_type=target_type,
            target_id=target_id,
            metadata={
                "reason": reason,
                "dry_run": dry_run,
            },
        )

        return {
            "action": "quarantine_memory",
            "target_id": target_id,
            "target_type": target_type,
            "reason": reason,
            "dry_run": dry_run,
            "changed": not dry_run,
            "rollback_data": {
                "target_id": target_id,
            },
        }

    async def expire_approvals(
        self,
        agent_id_or_scope: str,
        performed_by: str = "system",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Immediately expires pending approval requests for an agent or scope.
        """
        await self._validate_permission(performed_by)

        is_uuid = False
        parsed_uuid = None
        try:
            parsed_uuid = uuid.UUID(agent_id_or_scope)
            is_uuid = True
        except ValueError:
            pass

        # Select all pending approval requests matching the criteria
        if is_uuid:
            stmt = (
                select(AgentApprovalRequest)
                .join(AgentRun, AgentApprovalRequest.agent_run_id == AgentRun.id)
                .where(AgentApprovalRequest.status == "pending", AgentRun.agent_id == parsed_uuid)
            )
        else:
            stmt = select(AgentApprovalRequest).where(
                AgentApprovalRequest.status == "pending",
                AgentApprovalRequest.reviewer_role == agent_id_or_scope,
            )

        res = await self.db.execute(stmt)
        approvals = res.scalars().all()

        if not approvals:
            # Idempotent - no pending approvals found
            return {
                "action": "expire_approvals",
                "target": agent_id_or_scope,
                "expired_count": 0,
                "dry_run": dry_run,
                "changed": False,
                "rollback_data": {
                    "expired_ids": [],
                },
            }

        expired_ids = [str(a.id) for a in approvals]

        if not dry_run:
            now = utc_now()
            for approval in approvals:
                approval.status = "expired"
                approval.decided_by = performed_by
                approval.decided_at = now
                approval.updated_at = now
                self.db.add(approval)
            await self.db.commit()

        await record_admin_audit_event(
            self.db,
            event_type="agent.containment.expire_approvals",
            status="success" if not dry_run else "dry_run",
            actor_identifier=performed_by,
            target_type="agent_approval_request",
            target_id=agent_id_or_scope,
            metadata={
                "expired_count": len(approvals),
                "expired_ids": expired_ids,
                "dry_run": dry_run,
            },
        )

        return {
            "action": "expire_approvals",
            "target": agent_id_or_scope,
            "expired_count": len(approvals),
            "dry_run": dry_run,
            "changed": not dry_run,
            "rollback_data": {
                "expired_ids": expired_ids if not dry_run else [],
            },
        }

    async def throttle_queue(
        self,
        target_id: str,
        limit: int,
        performed_by: str = "system",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Sets a queue throttle limit for an agent or queue.
        """
        await self._validate_permission(performed_by)

        target_type = "queue"
        try:
            target_uuid = uuid.UUID(target_id)
            agent = await self.db.get(AgentDefinition, target_uuid)
            if agent:
                target_type = "agent"
        except ValueError:
            pass

        # Idempotency check: look up active throttle
        stmt = select(AgentQueueThrottle).where(
            AgentQueueThrottle.target_id == target_id, AgentQueueThrottle.is_active == True
        )
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()

        previous_limit = None
        changed = False

        if existing:
            previous_limit = existing.rate_limit
            if previous_limit == limit:
                # Idempotent
                return {
                    "action": "throttle_queue",
                    "target_id": target_id,
                    "target_type": target_type,
                    "limit": limit,
                    "previous_limit": previous_limit,
                    "dry_run": dry_run,
                    "changed": False,
                    "rollback_data": {
                        "target_id": target_id,
                        "previous_limit": previous_limit,
                    },
                }

            if not dry_run:
                existing.rate_limit = limit
                existing.throttled_by = performed_by
                existing.updated_at = utc_now()
                self.db.add(existing)
                await self.db.commit()
            changed = not dry_run
        else:
            if not dry_run:
                throttle = AgentQueueThrottle(
                    target_id=target_id,
                    target_type=target_type,
                    rate_limit=limit,
                    throttled_by=performed_by,
                    is_active=True,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                self.db.add(throttle)
                await self.db.commit()
            changed = not dry_run

        await record_admin_audit_event(
            self.db,
            event_type="agent.containment.throttle_queue",
            status="success" if not dry_run else "dry_run",
            actor_identifier=performed_by,
            target_type=target_type,
            target_id=target_id,
            metadata={
                "limit": limit,
                "previous_limit": previous_limit,
                "dry_run": dry_run,
            },
        )

        return {
            "action": "throttle_queue",
            "target_id": target_id,
            "target_type": target_type,
            "limit": limit,
            "previous_limit": previous_limit,
            "dry_run": dry_run,
            "changed": changed,
            "rollback_data": {
                "target_id": target_id,
                "previous_limit": previous_limit,
            },
        }

    async def rollback(
        self,
        action_type: str,
        rollback_data: dict[str, Any],
        performed_by: str = "system",
    ) -> dict[str, Any]:
        """
        Undoes/reverts a containment action.
        """
        await self._validate_permission(performed_by)

        report = {
            "action": f"rollback_{action_type}",
            "rollback_data": rollback_data,
            "status": "success",
        }

        if action_type == "disable_tool":
            tool_id = rollback_data.get("tool_id")
            previous_state = rollback_data.get("previous_state", True)
            if tool_id:
                tool_uuid = None
                try:
                    tool_uuid = uuid.UUID(tool_id)
                except ValueError:
                    pass

                if tool_uuid:
                    stmt = select(AgentTool).where(AgentTool.id == tool_uuid)
                else:
                    stmt = select(AgentTool).where(AgentTool.name == tool_id)

                res = await self.db.execute(stmt)
                tool = res.scalar_one_or_none()
                if tool:
                    tool.enabled = previous_state
                    self.db.add(tool)
                    await self.db.commit()
                    report["details"] = (
                        f"Restored tool {tool_id} enabled status to {previous_state}"
                    )
                else:
                    raise ValueError(f"Tool {tool_id} not found during rollback")

        elif action_type == "quarantine_memory":
            target_id = rollback_data.get("target_id")
            if target_id:
                stmt = select(AgentMemoryQuarantine).where(
                    AgentMemoryQuarantine.target_id == target_id
                )
                res = await self.db.execute(stmt)
                quarantine = res.scalar_one_or_none()
                if quarantine:
                    await self.db.delete(quarantine)
                    await self.db.commit()
                    report["details"] = f"Removed memory quarantine for {target_id}"
                else:
                    report["details"] = f"No active memory quarantine found for {target_id}"

        elif action_type == "expire_approvals":
            expired_ids = rollback_data.get("expired_ids", [])
            if expired_ids:
                uuids = []
                for eid in expired_ids:
                    try:
                        uuids.append(uuid.UUID(eid))
                    except ValueError:
                        pass

                if uuids:
                    stmt = select(AgentApprovalRequest).where(
                        AgentApprovalRequest.id.in_(uuids), AgentApprovalRequest.status == "expired"
                    )
                    res = await self.db.execute(stmt)
                    approvals = res.scalars().all()
                    for approval in approvals:
                        approval.status = "pending"
                        approval.decided_by = None
                        approval.decided_at = None
                        approval.updated_at = utc_now()
                        self.db.add(approval)
                    await self.db.commit()
                    report["details"] = (
                        f"Restored {len(approvals)} expired approvals back to pending status"
                    )
                else:
                    report["details"] = "No valid approval IDs provided for rollback"

        elif action_type == "throttle_queue":
            target_id = rollback_data.get("target_id")
            previous_limit = rollback_data.get("previous_limit")
            if target_id:
                stmt = select(AgentQueueThrottle).where(
                    AgentQueueThrottle.target_id == target_id, AgentQueueThrottle.is_active == True
                )
                res = await self.db.execute(stmt)
                throttle = res.scalar_one_or_none()
                if throttle:
                    if previous_limit is None:
                        # Deactivate or delete the throttle
                        throttle.is_active = False
                        self.db.add(throttle)
                        report["details"] = f"Deactivated queue throttle for {target_id}"
                    else:
                        throttle.rate_limit = previous_limit
                        self.db.add(throttle)
                        report["details"] = (
                            f"Restored queue throttle limit for {target_id} to {previous_limit}"
                        )
                    await self.db.commit()
                else:
                    report["details"] = f"No active queue throttle found for {target_id}"

        else:
            raise ValueError(f"Unknown action type: {action_type}")

        await record_admin_audit_event(
            self.db,
            event_type=f"agent.containment.rollback.{action_type}",
            status="success",
            actor_identifier=performed_by,
            target_type="containment_rollback",
            target_id=action_type,
            metadata={
                "rollback_data": rollback_data,
            },
        )

        return report
