from pathlib import Path
from unittest.mock import patch

import yaml

from scripts.llm_harness.install_wizard import (
    InstallAnswers,
    build_install_plan,
    write_install_artifacts,
)
from scripts.llm_harness.stack_cli import main


def _answers(tmp_path: Path, **overrides) -> InstallAnswers:
    values = {
        "has_gpu": False,
        "nvidia": False,
        "amd": False,
        "apple_silicon": False,
        "users": 5,
        "multi_tenant": False,
        "agentic": False,
        "kubernetes": False,
        "full_observability": False,
        "marketplace": False,
        "target_dir": tmp_path,
        "base_url": "http://localhost:18080",
        "host_port": 18080,
    }
    values.update(overrides)
    return InstallAnswers(**values)


def test_non_interactive_install_generates_files(tmp_path):
    exit_code = main(["install", "--non-interactive", "--target-dir", str(tmp_path)])

    assert exit_code == 0
    assert (tmp_path / "docker-compose.yml").exists()
    assert (tmp_path / ".env").exists()
    assert (tmp_path / "profile.yaml").exists()
    assert (tmp_path / "feature-flags.env").exists()


def test_lite_plan_omits_postgres_and_observability(tmp_path):
    plan = build_install_plan(_answers(tmp_path))
    write_install_artifacts(plan)

    compose = yaml.safe_load((tmp_path / "docker-compose.yml").read_text(encoding="utf-8"))
    profile = yaml.safe_load((tmp_path / "profile.yaml").read_text(encoding="utf-8"))

    assert plan.profile == "lite"
    assert "postgres" not in compose["services"]
    assert "prometheus" not in compose["services"]
    assert profile["profile"] == "lite"


def test_agentic_plan_enables_agent_worker(tmp_path):
    plan = build_install_plan(_answers(tmp_path, has_gpu=True, nvidia=True, users=20, agentic=True))
    write_install_artifacts(plan)

    compose = yaml.safe_load((tmp_path / "docker-compose.yml").read_text(encoding="utf-8"))
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")

    assert plan.profile == "agentic"
    assert "agent-worker" in compose["services"]
    assert "AGENT_RUNTIME_ENABLED=true" in env_text
    assert "GPU_VENDOR=nvidia" in env_text


def test_enterprise_plan_enables_observability_and_marketplace(tmp_path):
    plan = build_install_plan(
        _answers(
            tmp_path,
            users=250,
            multi_tenant=True,
            kubernetes=True,
            full_observability=True,
            marketplace=True,
        )
    )
    write_install_artifacts(plan)

    compose = yaml.safe_load((tmp_path / "docker-compose.yml").read_text(encoding="utf-8"))
    profile = yaml.safe_load((tmp_path / "profile.yaml").read_text(encoding="utf-8"))

    assert plan.profile == "enterprise"
    assert "postgres" in compose["services"]
    assert "prometheus" in compose["services"]
    assert "loki" in compose["services"]
    assert "tempo" in compose["services"]
    assert profile["features"]["PLUGIN_MARKETPLACE_ENABLED"] == "true"


def test_invalid_multiple_gpu_vendors_fails(tmp_path):
    with patch("sys.stderr"):
        exit_code = main(
            [
                "install",
                "--non-interactive",
                "--target-dir",
                str(tmp_path),
                "--gpu",
                "--nvidia",
                "--amd",
            ]
        )

    assert exit_code == 1
