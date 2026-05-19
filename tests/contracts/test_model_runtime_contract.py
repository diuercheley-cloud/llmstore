import pytest
from uuid import uuid4
from app.contracts.model_runtime import ModelRuntimeContract, ModelInstance, ModelRuntimeCapabilities

class MockRuntime(ModelRuntimeContract):
    async def load_model(self, model_id, backend_id, model_path, runtime_config=None) -> ModelInstance:
        return ModelInstance(
            id=uuid4(),
            model_id=model_id,
            backend_id=backend_id,
            status="ready",
            health_status="healthy",
            port=8080,
            is_active=True
        )

    async def unload_model(self, instance_id):
        pass

    async def activate_model(self, instance_id):
        pass

    async def get_model_health(self, instance_id):
        return {"status": "healthy"}

    def capabilities(self) -> ModelRuntimeCapabilities:
        return ModelRuntimeCapabilities(hot_swap=True)

    def validate_contract(self) -> bool:
        return True

@pytest.mark.asyncio
async def test_model_runtime_contract_implementation():
    runtime = MockRuntime()
    assert runtime.validate_contract() is True
    
    m_id = uuid4()
    b_id = uuid4()
    instance = await runtime.load_model(m_id, b_id, "model.gguf")
    assert instance.model_id == m_id
    assert instance.status == "ready"
    
    caps = runtime.capabilities()
    assert caps.hot_swap is True
