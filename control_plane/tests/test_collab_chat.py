import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.collab_chat.channel_service import ChannelService
from app.services.collab_chat.message_service import MessageService
from app.services.collab_chat.agent_participant import AgentParticipantService

@pytest.mark.asyncio
async def test_create_channel_and_add_member():
    session = AsyncMock()
    svc = ChannelService(session)
    
    tenant_id = "tenant-1"
    channel = await svc.create_channel(tenant_id, "Geral")
    
    assert channel.name == "Geral"
    assert channel.tenant_id == tenant_id
    
    member = await svc.add_member(channel.id, "user-1")
    assert member.user_id == "user-1"
    assert member.channel_id == channel.id

@pytest.mark.asyncio
async def test_post_message_triggers_mention():
    session = AsyncMock()
    msg_svc = MessageService(session)
    
    channel_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    content = f"Olá @[{agent_id}]"
    
    with patch("app.services.collab_chat.agent_participant.AgentParticipantService.trigger_agent_run", new_callable=AsyncMock) as mock_trigger:
        await msg_svc.create_message(channel_id, user_id="user-1", content=content)
        assert mock_trigger.called
        assert mock_trigger.call_args[0][1] == agent_id

@pytest.mark.asyncio
async def test_tenant_isolation_channels():
    session = AsyncMock()
    svc = ChannelService(session)
    
    # Mocking select results
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [MagicMock(tenant_id="tenant-1")]
    session.execute.return_value = mock_res
    
    channels = await svc.get_channels("tenant-1")
    assert len(channels) == 1
    assert channels[0].tenant_id == "tenant-1"
