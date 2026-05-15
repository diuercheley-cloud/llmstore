from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.commercial_runtime_fabric import CommercialRuntimeHealingAction
from datetime import datetime
import hmac
import hashlib
import os

class RuntimeHealingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.secret_key = os.getenv("HEALING_SECRET_KEY", "default-healing-secret")

    async def perform_action(self, action_id: str):
        stmt = select(CommercialRuntimeHealingAction).filter(CommercialRuntimeHealingAction.id == action_id)
        result = await self.db.execute(stmt)
        action = result.scalars().first()
        if not action:
            raise ValueError("Action not found")

        action.status = "executing"
        action.started_at = datetime.utcnow()
        await self.db.commit()

        try:
            result_data = await self._dispatch_action(action.action_type, action.target_id, action.parameters)
            action.status = "completed"
            action.result = result_data
            action.signed_receipt = self._sign_receipt(action_id, result_data)
        except Exception as e:
            action.status = "failed"
            action.result = {"error": str(e)}
        finally:
            action.finished_at = datetime.utcnow()
            await self.db.commit()

        return action

    async def _dispatch_action(self, action_type: str, target_id: str, parameters: dict):
        if action_type == "restart_service":
            return {"success": True, "message": f"Service {parameters.get('service')} restarted on {target_id}"}
        elif action_type == "rollback_state":
            return {"success": True, "message": f"State rolled back for {target_id}"}
        elif action_type == "replay_workflow":
            return {"success": True, "message": f"Workflow {target_id} replayed from step {parameters.get('from_step')}"}
        elif action_type == "isolate_node":
            return {"success": True, "message": f"Node {target_id} isolated from fabric"}
        elif action_type == "resync_mesh":
            return {"success": True, "message": f"Mesh resynced for {target_id}"}
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    def _sign_receipt(self, action_id: str, result: dict):
        message = f"{action_id}:{result}".encode()
        signature = hmac.new(self.secret_key.encode(), message, hashlib.sha256).hexdigest()
        return f"v1:{signature}"
