from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.billing_plan import BillingPlan
from app.models.inference_backend import InferenceBackend
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.utils.model_prompting import detect_architecture, detect_prompt_template
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_ALLOWED_DOCKER_SERVICES = {
    "data-plane-gemma",
    "data-plane-mock",
    "data-plane-ollama",
}
_QUANTIZATION_RE = re.compile(r"(Q\d(?:_[0-9A-Z]+)+|IQ\d(?:_[0-9A-Z]+)+|FP16|F16|BF16)", re.IGNORECASE)


@dataclass(slots=True)
class DockerCommandResult:
    ok: bool
    command: list[str]
    stdout: str
    stderr: str
    exit_code: int
    detail: str | None = None


def project_root() -> Path:
    """Find project root by looking for markers like VERSION or docker-compose.yml."""
    curr = Path(__file__).resolve()
    for parent in curr.parents:
        if (parent / "VERSION").exists() or (parent / "docker-compose.yml").exists():
            return parent
    return curr.parents[3]


def compose_file_path() -> Path | None:
    candidate = project_root() / "docker-compose.yml"
    return candidate if candidate.exists() else None


def resolve_models_dir() -> Path:
    settings = get_settings()
    configured = (settings.models_dir or "").strip()
    candidates = []
    if configured:
        configured_path = Path(configured)
        if not configured_path.is_absolute():
            configured_path = project_root() / configured_path
        candidates.append(configured_path)
    candidates.extend([Path("/models"), project_root() / "models"])
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists() and candidate.is_dir():
            return candidate
    if configured:
        configured_path = Path(configured)
        return configured_path if configured_path.is_absolute() else (project_root() / configured_path)
    return Path("/models")


def parse_metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def dump_metadata(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def merge_metadata(existing_raw: str | None, updates: dict[str, Any]) -> str:
    payload = parse_metadata(existing_raw)
    for key, value in updates.items():
        if value is None:
            payload.pop(key, None)
        else:
            payload[key] = value
    return dump_metadata(payload)


def display_name_for_model(model: ModelRegistry) -> str:
    metadata = parse_metadata(model.metadata_json)
    value = metadata.get("display_name")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return model.model_alias or model.model_id


def reasoning_defaults_for_model(model: ModelRegistry) -> dict[str, bool | None]:
    metadata = parse_metadata(model.metadata_json)
    allow_reasoning = metadata.get("allow_reasoning")
    include_reasoning_default = metadata.get("include_reasoning_default")
    return {
        "allow_reasoning": allow_reasoning if isinstance(allow_reasoning, bool) else None,
        "include_reasoning_default": include_reasoning_default if isinstance(include_reasoning_default, bool) else None,
    }


def architecture_for_model(model: ModelRegistry) -> str | None:
    return detect_architecture(
        model_id=model.model_id,
        model_file=model.model_file,
        model_alias=model.model_alias,
        metadata_json=model.metadata_json,
    )


def prompt_template_for_payload(
    *,
    prompt_template: str | None,
    model_id: str,
    model_file: str,
    model_alias: str | None,
    metadata_json: str | None,
) -> str | None:
    if prompt_template and prompt_template != "auto":
        return prompt_template
    return detect_prompt_template(
        model_id=model_id,
        model_file=model_file,
        model_alias=model_alias,
        metadata_json=metadata_json,
    ) or "auto"


def sanitize_model_filename(filename: str, *, provider: str) -> str:
    value = (filename or "").strip()
    if not value:
        raise ValueError("model file is required")
    
    # Remote/API-based providers use identifiers that might contain slashes
    if provider in ["openai_compatible", "ollama", "openai", "anthropic", "deepseek", "vllm"]:
        return value

    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("model file must stay inside /models")
    normalized = path.name
    if normalized != value:
        raise ValueError("model file must be a filename inside /models")
    if provider == "llama.cpp" and not normalized.lower().endswith(".gguf"):
        raise ValueError("llama.cpp models must use .gguf files")
    return normalized


def ensure_model_file_exists(filename: str, *, provider: str) -> Path:
    normalized = sanitize_model_filename(filename, provider=provider)
    models_dir = resolve_models_dir()
    candidate = (models_dir / normalized).resolve()
    if models_dir.exists() and models_dir.resolve() not in candidate.parents and candidate != models_dir.resolve():
        raise ValueError("model file must stay inside /models")
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(f"model file not found in {models_dir}")
    return candidate


def detect_quantization(filename: str) -> str | None:
    match = _QUANTIZATION_RE.search(filename)
    return match.group(1).upper() if match else None


async def list_model_files(session: AsyncSession) -> list[dict[str, Any]]:
    models_dir = resolve_models_dir()
    if not models_dir.exists() or not models_dir.is_dir():
        return []
    rows = (
        await session.execute(select(ModelRegistry.model_file, ModelRegistry.status))
    ).all()
    registered_files = {
        str(model_file): str(status or "")
        for model_file, status in rows
        if model_file
    }
    files = []
    for entry in sorted(models_dir.iterdir(), key=lambda item: item.name.lower()):
        if not entry.is_file() or not entry.name.lower().endswith(".gguf"):
            continue
        stat = entry.stat()
        architecture = detect_architecture(
            model_id=entry.name,
            model_file=entry.name,
            model_alias=entry.stem,
            metadata_json=None,
        )
        files.append(
            {
                "filename": entry.name,
                "relative_path": entry.name,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "detected_architecture": architecture,
                "quantization": detect_quantization(entry.name),
                "already_registered": entry.name in registered_files,
                "registered_status": registered_files.get(entry.name),
            }
        )
    return files


def backend_service_name(backend: InferenceBackend) -> str | None:
    metadata = parse_metadata(backend.metadata_json)
    value = metadata.get("service_name")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def backend_runtime_capabilities(backend: InferenceBackend) -> dict[str, Any]:
    settings = get_settings()
    service_name = backend_service_name(backend)
    compose_file = compose_file_path()
    return {
        "service_name": service_name,
        "compose_available": compose_file is not None,
        "docker_actions_allowed": bool(
            settings.test_tools_enabled
            and not settings.public_exposure
            and service_name in _ALLOWED_DOCKER_SERVICES
            and compose_file is not None
        ),
        "test_tools_enabled": settings.test_tools_enabled,
        "public_exposure": settings.public_exposure,
    }


def run_backend_docker_command(backend: InferenceBackend, *compose_args: str, timeout_seconds: int = 30) -> DockerCommandResult:
    capabilities = backend_runtime_capabilities(backend)
    if not capabilities["docker_actions_allowed"]:
        return DockerCommandResult(
            ok=False,
            command=[],
            stdout="",
            stderr="",
            exit_code=403,
            detail="docker actions disabled for this backend",
        )
    compose_file = compose_file_path()
    assert compose_file is not None
    command = ["docker", "compose", "-f", str(compose_file)]
    env_file = project_root() / ".env.local"
    if env_file.exists():
        command.extend(["--env-file", str(env_file)])
    command.extend(compose_args)
    try:
        result = subprocess.run(
            command,
            cwd=str(project_root()),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env={**os.environ},
        )
    except FileNotFoundError:
        return DockerCommandResult(
            ok=False,
            command=command,
            stdout="",
            stderr="docker compose not available",
            exit_code=127,
            detail="docker compose not available",
        )
    except subprocess.TimeoutExpired as exc:
        return DockerCommandResult(
            ok=False,
            command=command,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "timeout",
            exit_code=124,
            detail="docker command timed out",
        )
    return DockerCommandResult(
        ok=result.returncode == 0,
        command=command,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.returncode,
        detail=None if result.returncode == 0 else "docker command failed",
    )


def backend_container_snapshot(backend: InferenceBackend) -> dict[str, Any]:
    service_name = backend_service_name(backend)
    capabilities = backend_runtime_capabilities(backend)
    snapshot = {
        "service_name": service_name,
        "available": False,
        "container_found": False,
        "status": "unavailable",
        "raw": None,
        "detail": None,
        **capabilities,
    }
    if not service_name or not capabilities["compose_available"]:
        snapshot["detail"] = "compose metadata unavailable"
        return snapshot
    result = run_backend_docker_command(backend, "ps", "--format", "json")
    if not result.ok:
        snapshot["detail"] = result.detail or result.stderr.strip() or "docker status unavailable"
        snapshot["error"] = result.stderr.strip() or result.stdout.strip()
        return snapshot
    snapshot["available"] = True
    raw = result.stdout.strip()
    try:
        parsed = json.loads(raw) if raw else []
    except json.JSONDecodeError:
        parsed = []
    if isinstance(parsed, dict):
        services = [parsed]
    elif isinstance(parsed, list):
        services = parsed
    else:
        services = []
    service_row = next(
        (
            item
            for item in services
            if str(item.get("Service") or item.get("Name") or "").strip() == service_name
        ),
        None,
    )
    if service_row is None:
        snapshot["status"] = "not-created"
        snapshot["detail"] = "service not present in docker compose ps"
        return snapshot
    snapshot["container_found"] = True
    snapshot["status"] = str(service_row.get("State") or service_row.get("Status") or "unknown").lower()
    snapshot["raw"] = service_row
    return snapshot


async def sync_allowed_plans(
    session: AsyncSession,
    *,
    model: ModelRegistry,
    allowed_plan_codes: list[str] | None,
) -> None:
    if allowed_plan_codes is None:
        return
    rows = (await session.execute(select(BillingPlan))).scalars().all()
    requested = {item.strip() for item in allowed_plan_codes if item and item.strip()}
    unknown = sorted(requested - {plan.code for plan in rows})
    if unknown:
        raise ValueError(f"unknown billing plan codes: {', '.join(unknown)}")
    public_names = {model.model_id}
    if model.model_alias:
        public_names.add(model.model_alias)
    for plan in rows:
        current = set()
        if plan.allowed_models_json:
            try:
                parsed = json.loads(plan.allowed_models_json)
            except json.JSONDecodeError:
                parsed = []
            if isinstance(parsed, list):
                current = {str(item) for item in parsed if str(item).strip()}
        current -= public_names
        if plan.code in requested:
            current.add(model.model_id)
            if model.model_alias:
                current.add(model.model_alias)
        plan.allowed_models_json = json.dumps(sorted(current), ensure_ascii=True)
        plan.updated_at = utc_now()


async def remove_model_routes(session: AsyncSession, model: ModelRegistry) -> int:
    rows = (
        await session.execute(
            select(ModelBackendRoute).where(ModelBackendRoute.model_registry_id == model.id)
        )
    ).scalars().all()
    for row in rows:
        await session.delete(row)
    return len(rows)


def archive_model_identity(model: ModelRegistry) -> None:
    metadata = parse_metadata(model.metadata_json)
    metadata["deleted_public_model_id"] = model.model_id
    metadata["deleted_public_model_alias"] = model.model_alias
    metadata["deleted_at"] = utc_now().isoformat()
    suffix = str(model.id).split("-")[0]
    archived_model_id = f"{model.model_id}::deleted::{suffix}"
    model.model_id = archived_model_id[:255]
    if model.model_alias:
        archived_alias = f"{model.model_alias}-deleted-{suffix}"
        model.model_alias = archived_alias[:128]
    model.metadata_json = dump_metadata(metadata)
    model.is_active = False
    model.is_default = False
    model.status = "soft-deleted"
    model.inference_backend_id = None
    model.updated_at = utc_now()
