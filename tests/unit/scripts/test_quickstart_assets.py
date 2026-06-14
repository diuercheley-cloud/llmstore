from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_quickstart_compose_is_minimal_and_targets_official_image() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.quickstart.yml").read_text(encoding="utf-8"))

    assert list(compose["services"]) == ["quickstart"]
    service = compose["services"]["quickstart"]
    assert service["image"] == "ghcr.io/llm-inference-stack/quickstart:latest"
    assert service["gpus"] == "all"
    assert "quickstart_models:/models" in service["volumes"]
    assert "quickstart_data:/data/quickstart" in service["volumes"]


def test_quickstart_dockerfile_exposes_healthcheck_and_lite_profile() -> None:
    dockerfile = (ROOT / "Dockerfile.quickstart").read_text(encoding="utf-8")

    assert "FROM nvidia/cuda:12.6.3-runtime-ubuntu24.04" in dockerfile
    assert "OPERATIONAL_PROFILE=lite" in dockerfile
    assert "DATABASE_URL=sqlite+aiosqlite:////data/quickstart/llmstack.db" in dockerfile
    assert 'HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=10 \\' in dockerfile
    assert 'ENTRYPOINT ["tini", "--", "/app/scripts/deploy/quickstart-bootstrap.sh"]' in dockerfile


def test_quickstart_scripts_are_shell_valid() -> None:
    for relative_path in (
        "scripts/deploy/quickstart-bootstrap.sh",
        "scripts/deploy/quickstart-healthcheck.sh",
    ):
        subprocess.run(
            ["bash", "-n", str(ROOT / relative_path)],
            check=True,
            cwd=ROOT,
        )


def test_quickstart_bootstrap_configures_embedded_services() -> None:
    script = (ROOT / "scripts/deploy/quickstart-bootstrap.sh").read_text(encoding="utf-8")

    assert 'export OPERATIONAL_PROFILE="${OPERATIONAL_PROFILE:-lite}"' in script
    assert 'export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:////data/quickstart/llmstack.db}"' in script
    assert 'redis-server \\' in script
    assert '/opt/quickstart/llama-entrypoint.sh &' in script
    assert 'alembic -c /app/control_plane/alembic.ini upgrade head' in script
    assert 'python -m app.workers.generation_worker &' in script
    assert 'python -m app.workers.rag_worker &' in script
