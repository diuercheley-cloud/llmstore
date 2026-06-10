import pytest
from fastapi import FastAPI


@pytest.mark.asyncio
async def test_fake_redis_supports_basic_queue_and_ttl_operations(fake_redis):
    assert await fake_redis.ping() is True
    assert await fake_redis.set("cache:key", "value", ex=30) is True
    assert await fake_redis.get("cache:key") == "value"
    assert await fake_redis.ttl("cache:key") == 30
    assert await fake_redis.rpush("jobs", "job-1", "job-2") == 2
    assert await fake_redis.blpop("jobs", timeout=1) == ("jobs", "job-1")
    assert await fake_redis.llen("jobs") == 1


@pytest.mark.asyncio
async def test_async_client_fixture_uses_in_process_fastapi_app(app_client_factory):
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    client = await app_client_factory(app)
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
