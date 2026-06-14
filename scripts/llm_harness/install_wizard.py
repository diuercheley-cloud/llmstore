from __future__ import annotations

import argparse
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt
from rich.table import Table

console = Console()


@dataclass
class InstallAnswers:
    has_gpu: bool
    nvidia: bool
    amd: bool
    apple_silicon: bool
    users: int
    multi_tenant: bool
    agentic: bool
    kubernetes: bool
    full_observability: bool
    marketplace: bool
    target_dir: Path
    base_url: str
    host_port: int


@dataclass
class InstallPlan:
    answers: InstallAnswers
    profile: str
    accelerator: str
    feature_flags: dict[str, str]
    env: dict[str, str]
    compose: dict[str, Any]
    profile_manifest: dict[str, Any]


class InstallWizardError(ValueError):
    pass


def _bool_env(value: bool) -> str:
    return "true" if value else "false"


def _determine_accelerator(answers: InstallAnswers) -> str:
    vendors = [
        name
        for name, enabled in (
            ("nvidia", answers.nvidia),
            ("amd", answers.amd),
            ("apple_silicon", answers.apple_silicon),
        )
        if enabled
    ]
    if len(vendors) > 1:
        raise InstallWizardError("Choose at most one accelerator vendor.")
    if not answers.has_gpu:
        if vendors:
            raise InstallWizardError("GPU vendor cannot be selected when GPU support is disabled.")
        return "cpu"
    if vendors:
        return vendors[0]
    return "generic"


def determine_profile(answers: InstallAnswers) -> str:
    if (
        answers.multi_tenant
        or answers.kubernetes
        or answers.marketplace
        or answers.full_observability
        or answers.users > 100
    ):
        return "enterprise"
    if answers.agentic:
        return "agentic"
    if answers.users > 10 or answers.has_gpu:
        return "standard"
    return "lite"


def derive_feature_flags(answers: InstallAnswers, profile: str) -> dict[str, str]:
    accelerator = _determine_accelerator(answers)
    return {
        "OPERATIONAL_PROFILE": profile,
        "OBSERVABILITY_ENABLED": _bool_env(profile != "lite"),
        "OTLP_EXPORT_ENABLED": _bool_env(answers.full_observability),
        "AGENT_MEMORY_ENABLED": _bool_env(profile in {"agentic", "enterprise"}),
        "AGENT_MEMORY_SEARCH_ENABLED": _bool_env(profile in {"agentic", "enterprise"}),
        "AGENT_TOOL_REGISTRY_ENABLED": _bool_env(profile in {"agentic", "enterprise"}),
        "AGENT_TOOL_EXECUTION_ENABLED": _bool_env(profile in {"agentic", "enterprise"}),
        "AGENT_STATEFUL_WORKFLOWS_ENABLED": _bool_env(profile in {"agentic", "enterprise"}),
        "AGENT_RUNTIME_ENABLED": _bool_env(profile in {"agentic", "enterprise"}),
        "AGENT_EXECUTION_ENABLED": _bool_env(profile in {"agentic", "enterprise"}),
        "AGENT_WORKER_ENABLED": _bool_env(profile in {"agentic", "enterprise"}),
        "AGENT_MARKETPLACE_ENABLED": _bool_env(answers.marketplace),
        "PLUGIN_MARKETPLACE_ENABLED": _bool_env(answers.marketplace),
        "PLUGIN_RUNTIME_ENABLED": _bool_env(profile == "enterprise"),
        "MULTI_CLUSTER_ENABLED": _bool_env(profile == "enterprise"),
        "DISTRIBUTED_RUNTIME_ENABLED": _bool_env(profile == "enterprise"),
        "COMMERCIAL_FEDERATION_ENABLED": _bool_env(profile == "enterprise"),
        "COMMERCIAL_GOVERNANCE_FEDERATION_ENABLED": _bool_env(profile == "enterprise"),
        "AGENT_CLUSTER_FEDERATION_ENABLED": _bool_env(profile == "enterprise"),
        "KUBERNETES_MODE": _bool_env(answers.kubernetes),
        "RAG_ENABLED": "true",
        "CLOUD_PROVIDERS_ENABLED": _bool_env(profile == "enterprise"),
        "PROVIDERS_ENABLED": (
            "local"
            if profile == "lite"
            else "local,lmstudio,vllm"
            if profile in {"standard", "agentic"}
            else "local,lmstudio,vllm,openai,anthropic,deepseek,openrouter"
        ),
        "GPU_VENDOR": accelerator,
        "GPU_ENABLED": _bool_env(answers.has_gpu),
        "MARKETPLACE_ENABLED": _bool_env(answers.marketplace),
        "MULTI_TENANT_ENABLED": _bool_env(answers.multi_tenant),
        "PROMETHEUS_ENABLED": _bool_env(profile != "lite"),
        "LOKI_ENABLED": _bool_env(answers.full_observability),
        "TEMPO_ENABLED": _bool_env(answers.full_observability),
    }


def _database_url(profile: str) -> str:
    if profile == "lite":
        return "sqlite+aiosqlite:///./data/lite.db"
    return "postgresql+asyncpg://llmstack:llmstack@postgres:5432/llmstack"


def derive_env(
    answers: InstallAnswers,
    profile: str,
    feature_flags: dict[str, str],
) -> dict[str, str]:
    env = {
        "COMPOSE_PROJECT_NAME": "llmstack",
        "OPERATIONAL_PROFILE": profile,
        "HOST_PORT": str(answers.host_port),
        "CONTROL_PLANE_PORT": "8080",
        "APP_PUBLIC_URL": answers.base_url,
        "PUBLIC_BASE_URL": answers.base_url,
        "ADMIN_BASE_URL": f"{answers.base_url.rstrip('/')}/admin-dashboard",
        "API_BASE_URL": f"{answers.base_url.rstrip('/')}/v1",
        "DATABASE_URL": _database_url(profile),
        "REDIS_URL": "redis://redis:6379/0",
        "DATA_PLANE_BASE_URL": "http://data-plane-gemma:8081",
        "POSTGRES_DB": "llmstack",
        "POSTGRES_USER": "llmstack",
        "POSTGRES_PASSWORD": "llmstack",
        "REDIS_PORT": "6379",
        "ADMIN_TOKEN": secrets.token_hex(32),
        "JWT_SECRET": secrets.token_hex(32),
        "CREATE_TABLES_ON_STARTUP": _bool_env(profile == "lite"),
        "LLAMA_N_GPU_LAYERS": "999" if feature_flags["GPU_VENDOR"] == "nvidia" else "0",
        "PUBLIC_EXPOSURE": "false",
        "PUBLIC_SIGNUP_ENABLED": "false",
    }
    env.update(feature_flags)
    return env


def _relative_repo_root(target_dir: Path, repo_root: Path) -> str:
    rel = os.path.relpath(repo_root, target_dir)
    return rel if rel != "." else "."


def derive_compose(
    answers: InstallAnswers,
    profile: str,
    repo_root: Path,
) -> dict[str, Any]:
    rel_root = _relative_repo_root(answers.target_dir, repo_root)
    compose: dict[str, Any] = {
        "services": {
            "redis": {
                "image": "redis:7-alpine",
                "ports": ["${REDIS_PORT:-6379}:6379"],
                "healthcheck": {
                    "test": ["CMD", "redis-cli", "ping"],
                    "interval": "10s",
                    "timeout": "5s",
                    "retries": 5,
                },
            },
            "data-plane-gemma": {
                "build": {
                    "context": rel_root,
                    "dockerfile": "docker/data-plane/Dockerfile",
                },
                "environment": {
                    "MODEL_FILE": "${MODEL_FILE:-gemma-4-E4B-it-Q4_K_M.gguf}",
                    "LLAMA_SERVER_PORT": 8081,
                    "LLAMA_N_GPU_LAYERS": "${LLAMA_N_GPU_LAYERS:-0}",
                },
                "ports": ["8081:8081"],
                "volumes": [f"{rel_root}/models:/models"],
            },
            "control-plane": {
                "build": {
                    "context": rel_root,
                    "dockerfile": "docker/control-plane/Dockerfile",
                },
                "env_file": [".env"],
                "depends_on": ["redis", "data-plane-gemma"],
                "ports": ["${HOST_PORT:-18080}:8080"],
                "volumes": [
                    f"{rel_root}/control_plane:/app/control_plane",
                    f"{rel_root}/config:/config:ro",
                    f"{rel_root}/data:/data",
                ],
            },
            "control-plane-worker": {
                "build": {
                    "context": rel_root,
                    "dockerfile": "docker/control-plane/Dockerfile",
                },
                "env_file": [".env"],
                "depends_on": ["redis", "data-plane-gemma"],
                "command": [
                    "sh",
                    "-c",
                    "cd control_plane && alembic upgrade head && cd .. && python -m app.workers.generation_worker",
                ],
                "volumes": [
                    f"{rel_root}/control_plane:/app/control_plane",
                    f"{rel_root}/config:/config:ro",
                    f"{rel_root}/data:/data",
                ],
            },
            "rag-worker": {
                "build": {
                    "context": rel_root,
                    "dockerfile": "docker/control-plane/Dockerfile",
                },
                "env_file": [".env"],
                "depends_on": ["redis"],
                "command": ["bash", "-lc", "python -m app.workers.rag_worker"],
                "volumes": [
                    f"{rel_root}/control_plane:/app/control_plane",
                    f"{rel_root}/data:/data",
                ],
            },
        },
        "volumes": {},
    }

    if profile != "lite":
        compose["services"]["postgres"] = {
            "image": "postgres:16-alpine",
            "environment": {
                "POSTGRES_DB": "${POSTGRES_DB}",
                "POSTGRES_USER": "${POSTGRES_USER}",
                "POSTGRES_PASSWORD": "${POSTGRES_PASSWORD}",
            },
            "volumes": ["postgres_data:/var/lib/postgresql/data"],
            "healthcheck": {
                "test": ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 5,
            },
        }
        compose["services"]["control-plane"]["depends_on"].insert(0, "postgres")
        compose["services"]["control-plane-worker"]["depends_on"].insert(0, "postgres")
        compose["services"]["rag-worker"]["depends_on"].insert(0, "postgres")
        compose["volumes"]["postgres_data"] = None

    if profile in {"agentic", "enterprise"}:
        compose["services"]["agent-worker"] = {
            "build": {
                "context": rel_root,
                "dockerfile": "docker/control-plane/Dockerfile",
            },
            "env_file": [".env"],
            "depends_on": ["control-plane", "redis"],
            "command": ["bash", "-lc", "python -m app.workers.agent_worker"],
            "volumes": [
                f"{rel_root}/control_plane:/app/control_plane",
                f"{rel_root}/config:/config:ro",
                f"{rel_root}/data:/data",
            ],
        }

    if answers.full_observability:
        compose["services"]["prometheus"] = {
            "image": "prom/prometheus:v2.53.4",
            "ports": ["9090:9090"],
            "volumes": [
                f"{rel_root}/monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro",
            ],
        }
        compose["services"]["loki"] = {
            "image": "grafana/loki:3.4.2",
            "ports": ["3100:3100"],
        }
        compose["services"]["tempo"] = {
            "image": "grafana/tempo:2.7.1",
            "ports": ["3200:3200"],
        }

    if _determine_accelerator(answers) == "nvidia":
        compose["services"]["data-plane-gemma"]["gpus"] = "all"

    return compose


def build_profile_manifest(
    answers: InstallAnswers,
    profile: str,
    feature_flags: dict[str, str],
) -> dict[str, Any]:
    return {
        "profile": profile,
        "inputs": {
            "has_gpu": answers.has_gpu,
            "nvidia": answers.nvidia,
            "amd": answers.amd,
            "apple_silicon": answers.apple_silicon,
            "users": answers.users,
            "multi_tenant": answers.multi_tenant,
            "agentic": answers.agentic,
            "kubernetes": answers.kubernetes,
            "full_observability": answers.full_observability,
            "marketplace": answers.marketplace,
        },
        "features": feature_flags,
    }


def build_install_plan(
    answers: InstallAnswers,
    repo_root: Path | None = None,
) -> InstallPlan:
    repo_root = repo_root or Path(__file__).resolve().parents[2]
    accelerator = _determine_accelerator(answers)
    profile = determine_profile(answers)
    feature_flags = derive_feature_flags(answers, profile)
    feature_flags["GPU_VENDOR"] = accelerator
    env = derive_env(answers, profile, feature_flags)
    compose = derive_compose(answers, profile, repo_root)
    profile_manifest = build_profile_manifest(answers, profile, feature_flags)
    return InstallPlan(
        answers=answers,
        profile=profile,
        accelerator=accelerator,
        feature_flags=feature_flags,
        env=env,
        compose=compose,
        profile_manifest=profile_manifest,
    )


def _env_text(values: dict[str, str]) -> str:
    lines = [f"{key}={value}" for key, value in sorted(values.items())]
    return "\n".join(lines) + "\n"


def write_install_artifacts(plan: InstallPlan) -> list[Path]:
    target_dir = plan.answers.target_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    files = {
        target_dir / ".env": _env_text(plan.env),
        target_dir / "feature-flags.env": _env_text(plan.feature_flags),
        target_dir / "profile.yaml": yaml.safe_dump(
            plan.profile_manifest,
            sort_keys=False,
            allow_unicode=False,
        ),
        target_dir / "docker-compose.yml": yaml.safe_dump(
            plan.compose,
            sort_keys=False,
            allow_unicode=False,
        ),
    }

    for path, content in files.items():
        path.write_text(content, encoding="utf-8")

    return list(files)


def _ask_interactive(
    target_dir: Path,
    base_url: str,
    host_port: int,
) -> InstallAnswers:
    console.print(
        Panel.fit(
            "LLMStack Install Wizard\nGera `docker-compose.yml`, `.env`, `profile.yaml` e `feature-flags.env`.",
            title="Install",
        )
    )
    has_gpu = Confirm.ask("Possui GPU?", default=False)
    nvidia = Confirm.ask("NVIDIA?", default=False) if has_gpu else False
    amd = Confirm.ask("AMD?", default=False) if has_gpu and not nvidia else False
    apple_silicon = (
        Confirm.ask("Apple Silicon?", default=False)
        if has_gpu and not nvidia and not amd
        else False
    )
    users = IntPrompt.ask("Quantos usuários?", default=5)
    multi_tenant = Confirm.ask("Multi-tenant?", default=False)
    agentic = Confirm.ask("Agentic?", default=False)
    kubernetes = Confirm.ask("Kubernetes?", default=False)
    full_observability = Confirm.ask("Observabilidade completa?", default=False)
    marketplace = Confirm.ask("Marketplace?", default=False)
    return InstallAnswers(
        has_gpu=has_gpu,
        nvidia=nvidia,
        amd=amd,
        apple_silicon=apple_silicon,
        users=users,
        multi_tenant=multi_tenant,
        agentic=agentic,
        kubernetes=kubernetes,
        full_observability=full_observability,
        marketplace=marketplace,
        target_dir=target_dir,
        base_url=base_url,
        host_port=host_port,
    )


def render_plan_summary(plan: InstallPlan) -> None:
    table = Table(title="Plano de Instalação")
    table.add_column("Campo")
    table.add_column("Valor")
    table.add_row("Perfil", plan.profile)
    table.add_row("Acelerador", plan.accelerator)
    table.add_row("Usuários", str(plan.answers.users))
    table.add_row("Target", str(plan.answers.target_dir))
    table.add_row("Observabilidade", plan.feature_flags["OTLP_EXPORT_ENABLED"])
    table.add_row("Agentic", plan.feature_flags["AGENT_RUNTIME_ENABLED"])
    table.add_row("Marketplace", plan.feature_flags["PLUGIN_MARKETPLACE_ENABLED"])
    console.print(table)


def build_answers_from_args(args: argparse.Namespace) -> InstallAnswers:
    if args.interactive:
        return _ask_interactive(args.target_dir, args.base_url, args.host_port)
    return InstallAnswers(
        has_gpu=args.has_gpu,
        nvidia=args.nvidia,
        amd=args.amd,
        apple_silicon=args.apple_silicon,
        users=args.users,
        multi_tenant=args.multi_tenant,
        agentic=args.agentic,
        kubernetes=args.kubernetes,
        full_observability=args.full_observability,
        marketplace=args.marketplace,
        target_dir=args.target_dir,
        base_url=args.base_url,
        host_port=args.host_port,
    )


def run_install(args: argparse.Namespace) -> int:
    answers = build_answers_from_args(args)
    plan = build_install_plan(answers)
    render_plan_summary(plan)
    if args.interactive and not Confirm.ask("Gerar arquivos?", default=True):
        console.print("Operação cancelada.")
        return 1
    files = write_install_artifacts(plan)
    console.print(
        Panel.fit(
            "\n".join(str(path) for path in files),
            title="Arquivos gerados",
        )
    )
    return 0
