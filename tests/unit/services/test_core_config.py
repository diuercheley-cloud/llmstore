from control_plane.app.services.config.core_config import CoreConfig


def test_core_config_reads_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("DATA_PLANE_BASE_URL", "http://localhost:8081")

    config = CoreConfig()

    assert config.database_url == "postgresql+asyncpg://user:password@localhost:5432/db"
    assert config.redis_url == "redis://localhost:6379/0"
    assert config.data_plane_base_url == "http://localhost:8081"
    assert config.project_name == "local-llm-inference-stack"
    assert config.public_api_enabled is False


def test_core_config_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("DATA_PLANE_BASE_URL", "http://localhost:8081")

    config = CoreConfig()

    assert config.control_plane_port == 8080
    assert config.observability_enabled is True
    assert config.token_counting_real_enabled is True
