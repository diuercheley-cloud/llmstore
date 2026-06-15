# Owner: platform-operations
import uuid

from app.compat.autogen.adapters import ConversableAgent
from app.models.agents.agent_sessions import (
    AgentConversationThread,
    AgentSession,
    AgentThreadMessage,
)
from app.models.agents.agents import AgentDefinition
from sqlalchemy.ext.asyncio import AsyncSession


async def convert_autogen_agent_to_agent_definition(
    db: AsyncSession, tenant_id: str, agent: ConversableAgent, owner: str = "autogen-migrated"
) -> AgentDefinition:
    """
    Converts an AutoGen ConversableAgent to a native AgentDefinition.
    """
    # Try to extract model from llm_config
    model_id = "default-model"
    if agent.llm_config and "config_list" in agent.llm_config:
        config_list = agent.llm_config["config_list"]
        if config_list and isinstance(config_list, list) and isinstance(config_list[0], dict):
            model_id = config_list[0].get("model", "default-model")

    agent_def = AgentDefinition(
        id=uuid.uuid4(),
        name=agent.name,
        version="1.0.0",
        description=f"Migrated AutoGen Agent: {agent.name}",
        instructions=agent.system_message,
        model_id=model_id,
        owner=owner,
        tenant_id=tenant_id,
        status="active",
        allowed_tools=None,
    )
    db.add(agent_def)
    await db.flush()
    return agent_def


async def convert_autogen_chat_to_session(
    db: AsyncSession,
    tenant_id: str,
    agent_id: uuid.UUID,
    agent: ConversableAgent,
    recipient_name: str,
    user_id: str | None = None,
) -> AgentSession:
    """
    Converts an AutoGen chat history between agent and recipient into a native AgentSession,
    with a conversation thread and all exchange messages preserved.
    """
    # Create AgentSession
    session = AgentSession(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        agent_id=agent_id,
        status="active",
        session_metadata={
            "source": "autogen",
            "agent_name": agent.name,
            "recipient_name": recipient_name,
        },
    )
    db.add(session)

    # Create Conversation Thread
    thread = AgentConversationThread(id=uuid.uuid4(), session_id=session.id, status="active")
    db.add(thread)

    # Add messages
    history = agent.chat_history.get(recipient_name, [])
    for idx, msg in enumerate(history):
        thread_msg = AgentThreadMessage(
            id=uuid.uuid4(),
            thread_id=thread.id,
            session_id=session.id,
            role=msg.get("role", "user"),
            content=msg.get("content", ""),
            message_metadata={"sequence_number": idx},
        )
        db.add(thread_msg)

    await db.flush()
    return session
