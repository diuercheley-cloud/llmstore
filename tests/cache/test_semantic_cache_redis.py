import pytest
import json
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.cache.semantic_cache_redis import SemanticCacheRedis

@pytest.fixture
def mock_redis():
    redis = MagicMock() # Use MagicMock for the base to avoid auto-coroutine behavior
    redis.hgetall = AsyncMock(return_value={})
    redis.hset = AsyncMock()
    redis.hdel = AsyncMock()
    redis.zadd = AsyncMock()
    redis.zcard = AsyncMock(return_value=0)
    redis.zpopmin = AsyncMock(return_value=[])
    redis.expire = AsyncMock()
    
    pipeline = AsyncMock()
    pipeline.execute = AsyncMock()
    pipeline.hset = MagicMock()
    pipeline.zadd = MagicMock()
    pipeline.expire = MagicMock()
    
    # Mock the context manager
    pipe_mock = MagicMock()
    pipe_mock.__aenter__ = AsyncMock(return_value=pipeline)
    pipe_mock.__aexit__ = AsyncMock(return_value=None)
    
    redis.pipeline.return_value = pipe_mock
    return redis

@pytest.fixture
def mock_embedding_service():
    service = MagicMock()
    service.model_name = "test-model"
    service.embed_text = AsyncMock(return_value=[1.0, 0.0, 0.0])
    return service

@pytest.mark.asyncio
async def test_semantic_cache_hit(mock_redis, mock_embedding_service):
    with patch("app.services.cache.semantic_cache_redis.get_embedding_service", return_value=mock_embedding_service), \
         patch("app.services.cache.semantic_cache_redis.settings") as mock_settings:
        
        mock_settings.semantic_cache_enabled = True
        mock_settings.semantic_cache_threshold = 0.9
        
        cache = SemanticCacheRedis(mock_redis)
        
        # Setup stored entry: very similar vector (cosine similarity ~0.99)
        entry = {
            "p": "hello world",
            "resp": {"output": "hi there"},
            "vec": [0.99, 0.1, 0.0],
            "emb_model": "test-model"
        }
        mock_redis.hgetall.return_value = {"entry1": json.dumps(entry)}
        
        # Test get
        result = await cache.get("tenant1", "client1", "gpt-4", "hello")
        
        assert result == {"output": "hi there"}
        mock_redis.zadd.assert_called()

@pytest.mark.asyncio
async def test_semantic_cache_miss_low_similarity(mock_redis, mock_embedding_service):
    with patch("app.services.cache.semantic_cache_redis.get_embedding_service", return_value=mock_embedding_service), \
         patch("app.services.cache.semantic_cache_redis.settings") as mock_settings:
        
        mock_settings.semantic_cache_enabled = True
        mock_settings.semantic_cache_threshold = 0.9
        
        cache = SemanticCacheRedis(mock_redis)
        
        # Setup stored entry with very different vector (orthogonal)
        entry = {
            "p": "something else",
            "resp": {"output": "no match"},
            "vec": [0.0, 1.0, 0.0],
            "emb_model": "test-model"
        }
        mock_redis.hgetall.return_value = {"entry1": json.dumps(entry)}
        
        # Test get
        result = await cache.get("tenant1", "client1", "gpt-4", "hello")
        
        assert result is None

@pytest.mark.asyncio
async def test_semantic_cache_tenant_isolation(mock_redis, mock_embedding_service):
    with patch("app.services.cache.semantic_cache_redis.get_embedding_service", return_value=mock_embedding_service), \
         patch("app.services.cache.semantic_cache_redis.settings") as mock_settings:
        
        mock_settings.semantic_cache_enabled = True
        cache = SemanticCacheRedis(mock_redis)
        
        # Test get for tenant1
        await cache.get("tenant1", "client1", "gpt-4", "hello")
        mock_redis.hgetall.assert_any_call("semcache:tenant1:client1:gpt-4:entries")
        
        # Test get for tenant2
        await cache.get("tenant2", "client2", "gpt-4", "hello")
        mock_redis.hgetall.assert_any_call("semcache:tenant2:client2:gpt-4:entries")

@pytest.mark.asyncio
async def test_semantic_cache_model_invalidation(mock_redis, mock_embedding_service):
    with patch("app.services.cache.semantic_cache_redis.get_embedding_service", return_value=mock_embedding_service), \
         patch("app.services.cache.semantic_cache_redis.settings") as mock_settings:
        
        mock_settings.semantic_cache_enabled = True
        cache = SemanticCacheRedis(mock_redis)
        
        # Entry with different model version
        entry = {
            "p": "hello",
            "resp": {"output": "old version"},
            "vec": [1.0, 0.0, 0.0],
            "emb_model": "old-model-v1"
        }
        mock_redis.hgetall.return_value = {"entry1": json.dumps(entry)}
        
        # Test get (should miss because model mismatch)
        result = await cache.get("tenant1", "client1", "gpt-4", "hello")
        assert result is None

@pytest.mark.asyncio
async def test_semantic_cache_set_and_limit(mock_redis, mock_embedding_service):
    with patch("app.services.cache.semantic_cache_redis.get_embedding_service", return_value=mock_embedding_service), \
         patch("app.services.cache.semantic_cache_redis.settings") as mock_settings:
        
        mock_settings.semantic_cache_enabled = True
        mock_settings.semantic_cache_max_size = 2
        mock_settings.semantic_cache_ttl_seconds = 3600
        
        cache = SemanticCacheRedis(mock_redis)
        
        # Mock ZCARD to simulate limit exceeded
        mock_redis.zcard.return_value = 3
        mock_redis.zpopmin.return_value = [("entry_to_remove", 123456)]
        
        await cache.set("tenant1", "client1", "gpt-4", "hello", {"output": "val"})
        
        # Check if pipeline was used
        mock_redis.pipeline.assert_called()
        # Check if limit enforcement was called
        mock_redis.zcard.assert_called()
        mock_redis.zpopmin.assert_called()
        mock_redis.hdel.assert_called_with("semcache:tenant1:client1:gpt-4:entries", "entry_to_remove")
