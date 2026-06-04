import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.agents.memory.redis_memory_store import RedisMemoryStore


@pytest.fixture
def mock_redis():
    r = MagicMock()
    r.hset = AsyncMock()
    r.hgetall = AsyncMock()
    r.hdel = AsyncMock()
    return r


@pytest.fixture
def store(mock_redis):
    s = RedisMemoryStore(redis_client=mock_redis)
    return s


class TestRedisMemoryStore:
    @pytest.mark.asyncio
    async def test_add_item(self, store, mock_redis):
        tenant_id = "tenant-1"
        agent_id = uuid.uuid4()
        memory_id = uuid.uuid4()
        embedding = [0.1, 0.2, 0.3]

        await store.add_item(tenant_id, agent_id, memory_id, embedding, {"type": "chat"})

        key = f"agent:memory:vector:{tenant_id}"
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == key
        assert call_args[0][1] == str(memory_id)

    @pytest.mark.asyncio
    async def test_search_returns_matching_items(self, store, mock_redis):
        tenant_id = "tenant-1"
        agent_id = uuid.uuid4()
        memory_id = uuid.uuid4()

        item = {
            "agent_id": str(agent_id),
            "memory_id": str(memory_id),
            "embedding": json.dumps([0.1, 0.2, 0.3]),
            "metadata": json.dumps({"type": "chat"}),
        }
        mock_redis.hgetall.return_value = {str(memory_id): json.dumps(item)}

        results = await store.search(tenant_id, agent_id, [0.1, 0.2, 0.3], top_k=5)
        assert len(results) == 1
        assert results[0]["memory_id"] == memory_id
        assert results[0]["provider"] == "redis"

    @pytest.mark.asyncio
    async def test_search_empty_when_no_items(self, store, mock_redis):
        mock_redis.hgetall.return_value = {}
        results = await store.search("t1", uuid.uuid4(), [0.1], top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_filters_by_agent(self, store, mock_redis):
        agent_a = uuid.uuid4()
        agent_b = uuid.uuid4()

        items = {
            str(uuid.uuid4()): json.dumps({
                "agent_id": str(agent_a),
                "memory_id": str(uuid.uuid4()),
                "embedding": json.dumps([0.1, 0.2]),
                "metadata": "{}",
            }),
            str(uuid.uuid4()): json.dumps({
                "agent_id": str(agent_b),
                "memory_id": str(uuid.uuid4()),
                "embedding": json.dumps([0.3, 0.4]),
                "metadata": "{}",
            }),
        }
        mock_redis.hgetall.return_value = items

        results = await store.search("t1", agent_a, [0.1, 0.2], top_k=5)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_with_score_threshold(self, store, mock_redis):
        agent_id = uuid.uuid4()

        items = {
            str(uuid.uuid4()): json.dumps({
                "agent_id": str(agent_id),
                "memory_id": str(uuid.uuid4()),
                "embedding": json.dumps([1.0, 0.0]),
                "metadata": "{}",
            }),
        }
        mock_redis.hgetall.return_value = items

        results = await store.search("t1", agent_id, [0.0, 1.0], top_k=5, score_threshold=0.9)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_returns_top_k(self, store, mock_redis):
        agent_id = uuid.uuid4()
        items = {}
        for i in range(10):
            mid = uuid.uuid4()
            items[str(mid)] = json.dumps({
                "agent_id": str(agent_id),
                "memory_id": str(mid),
                "embedding": json.dumps([0.1, float(i) / 10.0]),
                "metadata": "{}",
            })
        mock_redis.hgetall.return_value = items

        results = await store.search("t1", agent_id, [0.1, 0.5], top_k=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_delete_item(self, store, mock_redis):
        tenant_id = "tenant-1"
        memory_id = uuid.uuid4()

        await store.delete_item(tenant_id, memory_id)

        key = f"agent:memory:vector:{tenant_id}"
        mock_redis.hdel.assert_called_once_with(key, str(memory_id))
