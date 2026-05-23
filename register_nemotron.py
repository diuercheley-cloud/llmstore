# Owner: agent-platform
import asyncio
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import get_settings

async def register_model():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    
    model_id = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    model_alias = "nemotron-reasoning-free"
    # Mapping requested model from user request to alias or ID
    user_requested_model = "nemotron-3-nano-omni-30b-a3b-reasoning"

    async with AsyncSession(engine) as session:
        # 1. Get OpenRouter backend ID
        result = await session.execute(text("SELECT id FROM inference_backends WHERE provider = 'openrouter' AND is_active = true LIMIT 1"))
        backend_row = result.fetchone()
        if not backend_row:
            print("Error: OpenRouter backend not found or inactive.")
            return
        backend_id = backend_row[0]

        # 2. Check if already exists
        result = await session.execute(text("SELECT id FROM model_registry WHERE model_id = :mid"), {"mid": model_id})
        if result.fetchone():
            print(f"Model {model_id} already registered.")
            return

        # 3. Insert into model_registry
        reg_id = str(uuid.uuid4())
        await session.execute(text("""
            INSERT INTO model_registry (id, model_id, model_alias, provider, model_file, is_active, is_default, created_at, updated_at)
            VALUES (:id, :mid, :alias, 'openrouter', :mfile, true, false, now(), now())
        """), {"id": reg_id, "mid": model_id, "alias": user_requested_model, "mfile": model_id})

        # 4. Insert into model_backend_routes
        await session.execute(text("""
            INSERT INTO model_backend_routes (id, model_registry_id, inference_backend_id, priority, weight, state, created_at, updated_at)
            VALUES (:id, :reg_id, :backend_id, 1, 100, 'healthy', now(), now())
        """), {"id": str(uuid.uuid4()), "reg_id": reg_id, "backend_id": backend_id})

        await session.commit()
        print(f"Successfully registered {model_id} with alias {user_requested_model}")

if __name__ == "__main__":
    asyncio.run(register_model())
