import logging
import uuid

from app.models.agents.agents import AgentDefinition
from app.models.agents.collab_chat import ChatAgentParticipant
from app.services.agents.agent_runtime import start_run
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentParticipantService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_agent_to_channel(
        self, channel_id: uuid.UUID, agent_id: uuid.UUID, auto_reply: bool = False
    ):
        participant = ChatAgentParticipant(
            channel_id=channel_id, agent_id=agent_id, auto_reply=auto_reply
        )
        self.db.add(participant)
        await self.db.flush()
        return participant

    async def trigger_agent_run(
        self, channel_id: uuid.UUID, agent_id: uuid.UUID, user_id: str, prompt: str
    ):
        # 1. Get agent and channel info
        agent = await self.db.get(AgentDefinition, agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} not found for collab chat")
            return

        # 2. Start an AgentRun
        try:
            run = await start_run(
                db=self.db,
                agent_id=agent_id,
                tenant_id=agent.tenant_id or "default",
                user_id=user_id,
                input_text=prompt,
                correlation_id=f"chat_channel_{channel_id}",
            )

            # 3. Post the agent's response back to the channel
            # We need to wait for the run to complete if it's sync, or listen to events if it's async.
            # For this simplified implementation, we'll wait and refresh the run.
            await self.db.refresh(run)

            from .message_service import MessageService

            msg_svc = MessageService(self.db)

            output_text = "Solicitação recebida. O agente está processando..."
            if run.status == "completed":
                # Assuming output is stored somewhere or we need to fetch it
                # In this system, output might be in a final step or an output_hash
                output_text = f"Agente processou a solicitação. Status: {run.status}"

            await msg_svc.create_message(
                channel_id=channel_id,
                agent_id=agent_id,
                content=output_text,
                message_type="agent_response",
                metadata={"run_id": str(run.id)},
            )
            await self.db.commit()
        except Exception as e:
            logger.exception(f"Agent run failed in collab chat: {e}")
