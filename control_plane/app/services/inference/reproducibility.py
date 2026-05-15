from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.request_context import get_correlation_id
from app.models.commercial_inference_reproducibility import (
    CommercialInferenceReproducibilityRecord,
    CommercialInferenceRuntimeSnapshot,
)
from app.models.commercial_model_supply_chain import CommercialSignedModelRegistryEntry
from app.services.admin_model_management import detect_quantization
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.utils.model_prompting import detect_architecture


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _safe_text(value: Any, *, limit: int = 2000) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    return text[:limit] or None


def _parse_metadata(raw: str | dict[str, Any] | None) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.lower().split())


def _extract_prompt_text(request_payload: dict[str, Any] | None) -> str:
    if not request_payload:
        return ""
    if isinstance(request_payload.get("prompt"), str):
        return request_payload["prompt"]
    parts: list[str] = []
    for message in request_payload.get("messages") or []:
        content = message.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
    return "\n".join(parts)


def _extract_response_text(response_payload: dict[str, Any] | None) -> str:
    if not response_payload:
        return ""
    choices = response_payload.get("choices")
    if isinstance(choices, list) and choices:
        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
    output_text = response_payload.get("output_text")
    if isinstance(output_text, str):
        return output_text
    output = response_payload.get("output")
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            message = item.get("message") or {}
            for part in message.get("content") or []:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(part["text"])
        return "\n".join(parts)
    return ""


def hash_prompt(prompt: str | dict[str, Any] | None) -> str:
    if isinstance(prompt, dict):
        return _sha256_payload(sanitize_report_payload(prompt))
    return hashlib.sha256((_normalize_text(prompt) or "").encode("utf-8")).hexdigest()


def hash_response(response: str | dict[str, Any] | None) -> str:
    if isinstance(response, dict):
        return _sha256_payload(sanitize_report_payload(response))
    return hashlib.sha256((_normalize_text(response) or "").encode("utf-8")).hexdigest()


def calculate_runtime_hash(snapshot: dict[str, Any]) -> str:
    return _sha256_payload(sanitize_report_payload(snapshot))


def build_runtime_snapshot(
    *,
    model_name: str,
    backend_name: str | None,
    provider: str | None,
    runtime_engine: str | None = None,
    runtime_engine_version: str | None = None,
    prompt_template: str | None = None,
    model_manifest_hash: str | None = None,
    model_checksum: str | None = None,
    request_payload: dict[str, Any] | None = None,
    model_metadata_json: str | dict[str, Any] | None = None,
    backend_metadata_json: str | dict[str, Any] | None = None,
    tokenizer_name: str | None = None,
    tokenizer_version: str | None = None,
) -> dict[str, Any]:
    model_metadata = _parse_metadata(model_metadata_json)
    backend_metadata = _parse_metadata(backend_metadata_json)
    architecture = detect_architecture(
        model_id=model_name,
        model_file=str(model_metadata.get("model_file") or model_name),
        model_alias=str(model_metadata.get("model_alias") or ""),
        metadata_json=json.dumps(model_metadata) if model_metadata else None,
    )
    chat_template = request_payload.get("chat_template") if request_payload else None
    chat_template_hash = hash_prompt(chat_template or prompt_template) if (chat_template or prompt_template) else None
    runtime_config = sanitize_report_payload(
        {
            "prompt_template": prompt_template,
            "chat_template_hash": chat_template_hash,
            "temperature": request_payload.get("temperature") if request_payload else None,
            "top_p": request_payload.get("top_p") if request_payload else None,
            "top_k": request_payload.get("top_k") if request_payload else None,
            "min_p": request_payload.get("min_p") if request_payload else None,
            "repetition_penalty": request_payload.get("repetition_penalty") if request_payload else request_payload.get("repeat_penalty") if request_payload else None,
            "max_tokens": request_payload.get("max_tokens") if request_payload else None,
            "quantization": model_metadata.get("quantization") or detect_quantization(str(model_metadata.get("model_file") or model_name)),
            "backend_metadata": backend_metadata,
            "architecture": architecture,
        }
    )
    tokenizer_info = {
        "tokenizer_name": tokenizer_name or model_metadata.get("tokenizer_name") or architecture or model_name,
        "tokenizer_version": tokenizer_version or model_metadata.get("tokenizer_version") or backend_metadata.get("tokenizer_version"),
        "template_hash": chat_template_hash,
        "architecture": architecture,
    }
    snapshot = {
        "backend_name": backend_name or provider or "unknown",
        "runtime_engine": runtime_engine or provider or "unknown",
        "runtime_engine_version": runtime_engine_version or str(backend_metadata.get("runtime_engine_version") or backend_metadata.get("version") or ""),
        "model_name": model_name,
        "model_manifest_hash": model_manifest_hash,
        "model_checksum": model_checksum,
        "runtime_config_json": runtime_config,
        "tokenizer_info_json": tokenizer_info,
        "snapshot_hash": "",
    }
    snapshot["snapshot_hash"] = calculate_runtime_hash(snapshot)
    return snapshot


def compare_outputs(
    original_output: str | dict[str, Any] | None,
    replay_output: str | dict[str, Any] | None,
) -> dict[str, Any]:
    original_text = original_output if isinstance(original_output, str) else _extract_response_text(original_output)
    replay_text = replay_output if isinstance(replay_output, str) else _extract_response_text(replay_output)
    original_hash = hash_response(original_output)
    replay_hash = hash_response(replay_output)
    original_normalized = _normalize_text(original_text)
    replay_normalized = _normalize_text(replay_text)

    original_tokens = set(token for token in original_normalized.split(" ") if token)
    replay_tokens = set(token for token in replay_normalized.split(" ") if token)
    union = original_tokens | replay_tokens
    intersection = original_tokens & replay_tokens
    token_overlap = 1.0 if not union else round(len(intersection) / len(union), 4)

    from app.services.inference.replay_verification import calculate_distance, calculate_similarity

    distance = calculate_distance(original_normalized, replay_normalized)
    similarity = calculate_similarity(
        original_text=original_text,
        replay_text=replay_text,
        original_hash=original_hash,
        replay_hash=replay_hash,
        token_overlap=token_overlap,
        distance=distance,
    )
    return {
        "original_hash": original_hash,
        "replay_hash": replay_hash,
        "exact_hash_match": original_hash == replay_hash,
        "normalized_text_match": original_normalized == replay_normalized,
        "token_overlap_ratio": token_overlap,
        "edit_distance": distance,
        "similarity": similarity,
        "distance": round(1.0 - similarity, 4),
        "original_text_length": len(original_text or ""),
        "replay_text_length": len(replay_text or ""),
    }


def compare_runtime_snapshots(
    original_snapshot: dict[str, Any] | CommercialInferenceRuntimeSnapshot | None,
    replay_snapshot: dict[str, Any] | CommercialInferenceRuntimeSnapshot | None,
) -> dict[str, Any]:
    def _snapshot_dict(value: dict[str, Any] | CommercialInferenceRuntimeSnapshot | None) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        return {
            "backend_name": value.backend_name,
            "runtime_engine": value.runtime_engine,
            "runtime_engine_version": value.runtime_engine_version,
            "model_name": value.model_name,
            "model_manifest_hash": value.model_manifest_hash,
            "runtime_config_json": value.runtime_config_json or {},
            "tokenizer_info_json": value.tokenizer_info_json or {},
            "snapshot_hash": value.snapshot_hash,
        }

    original = _snapshot_dict(original_snapshot)
    replay = _snapshot_dict(replay_snapshot)
    original_cfg = original.get("runtime_config_json") or {}
    replay_cfg = replay.get("runtime_config_json") or {}
    original_tok = original.get("tokenizer_info_json") or {}
    replay_tok = replay.get("tokenizer_info_json") or {}

    drifts: list[str] = []
    if (original_tok.get("tokenizer_name"), original_tok.get("tokenizer_version")) != (
        replay_tok.get("tokenizer_name"),
        replay_tok.get("tokenizer_version"),
    ):
        drifts.append("tokenizer_drift")
    if original_tok.get("template_hash") != replay_tok.get("template_hash"):
        drifts.append("template_drift")
    if original.get("runtime_engine") != replay.get("runtime_engine") or original.get("runtime_engine_version") != replay.get("runtime_engine_version"):
        drifts.append("runtime_drift")
    if original.get("model_manifest_hash") != replay.get("model_manifest_hash"):
        drifts.append("manifest_drift")
    if original_cfg.get("quantization") != replay_cfg.get("quantization"):
        drifts.append("quantization_drift")
    if original.get("snapshot_hash") != replay.get("snapshot_hash") and "runtime_drift" not in drifts:
        drifts.append("runtime_config_drift")
    return {
        "matched": not drifts,
        "drifts": drifts,
        "tokenizer_drift": "tokenizer_drift" in drifts,
        "template_drift": "template_drift" in drifts,
        "runtime_drift": any(item in drifts for item in {"runtime_drift", "runtime_config_drift", "manifest_drift"}),
        "quantization_drift": "quantization_drift" in drifts,
        "original_snapshot_hash": original.get("snapshot_hash"),
        "replay_snapshot_hash": replay.get("snapshot_hash"),
    }


async def _resolve_registry_entry(
    session: AsyncSession,
    *,
    model_name: str,
    model_alias: str | None,
) -> CommercialSignedModelRegistryEntry | None:
    result = await session.execute(
        select(CommercialSignedModelRegistryEntry)
        .where(
            or_(
                CommercialSignedModelRegistryEntry.model_name == model_name,
                CommercialSignedModelRegistryEntry.model_alias == model_alias,
            )
        )
        .order_by(desc(CommercialSignedModelRegistryEntry.updated_at), desc(CommercialSignedModelRegistryEntry.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


def determine_seed_capture(
    *,
    request_payload: dict[str, Any] | None,
    provider: str | None,
) -> dict[str, Any]:
    payload = request_payload or {}
    explicit_seed = payload.get("seed")
    stochastic = any(
        payload.get(key) not in (None, 0, 0.0, 1, 1.0)
        for key in ("temperature", "top_p", "top_k", "min_p", "repetition_penalty", "repeat_penalty")
    )
    backend_supports_seed = provider in {"llama.cpp", "ollama", "vllm", "openai_compatible", "local"}
    if explicit_seed is not None:
        return {
            "seed": int(explicit_seed),
            "seed_source": "explicit",
            "replay_supported": backend_supports_seed or not stochastic,
            "backend_supports_seed": backend_supports_seed,
        }
    if backend_supports_seed:
        implicit_seed = int(hash_prompt(payload)[:8], 16)
        return {
            "seed": implicit_seed,
            "seed_source": "implicit",
            "replay_supported": True,
            "backend_supports_seed": True,
        }
    return {
        "seed": None,
        "seed_source": "unsupported",
        "replay_supported": not stochastic,
        "backend_supports_seed": False,
    }


async def capture_reproducibility_record(
    session: AsyncSession,
    *,
    request_id: str | None,
    correlation_id: str | None,
    client_id: str | None,
    model_name: str,
    model_alias: str | None = None,
    provider: str | None = None,
    backend_name: str | None = None,
    request_payload: dict[str, Any] | None = None,
    response_payload: dict[str, Any] | None = None,
    prompt_template: str | None = None,
    tokenizer_name: str | None = None,
    tokenizer_version: str | None = None,
    runtime_engine: str | None = None,
    runtime_engine_version: str | None = None,
    model_metadata_json: str | dict[str, Any] | None = None,
    backend_metadata_json: str | dict[str, Any] | None = None,
    metadata_json: dict[str, Any] | None = None,
    replay_status: str = "original",
) -> CommercialInferenceReproducibilityRecord:
    cfg = get_settings()
    sanitized_metadata = sanitize_report_payload(metadata_json or {})
    if metadata_json and isinstance(metadata_json.get("replay_runtime_snapshot"), dict):
        sanitized_metadata["replay_runtime_snapshot"] = metadata_json["replay_runtime_snapshot"]
    registry_entry = await _resolve_registry_entry(session, model_name=model_name, model_alias=model_alias)
    seed_capture = determine_seed_capture(request_payload=request_payload, provider=provider)
    if request_payload is not None and request_payload.get("seed") is None and seed_capture["seed"] is not None and seed_capture["backend_supports_seed"]:
        request_payload = dict(request_payload)
        request_payload["seed"] = seed_capture["seed"]
    snapshot = build_runtime_snapshot(
        model_name=model_name,
        backend_name=backend_name,
        provider=provider,
        runtime_engine=runtime_engine,
        runtime_engine_version=runtime_engine_version,
        prompt_template=prompt_template,
        model_manifest_hash=registry_entry.manifest_hash if registry_entry else None,
        model_checksum=registry_entry.checksum_sha256 if registry_entry else None,
        request_payload=request_payload,
        model_metadata_json=model_metadata_json,
        backend_metadata_json=backend_metadata_json,
        tokenizer_name=tokenizer_name,
        tokenizer_version=tokenizer_version,
    )
    existing_snapshot = (
        await session.execute(
            select(CommercialInferenceRuntimeSnapshot).where(
                CommercialInferenceRuntimeSnapshot.snapshot_hash == snapshot["snapshot_hash"]
            )
        )
    ).scalar_one_or_none()
    if existing_snapshot is None:
        existing_snapshot = CommercialInferenceRuntimeSnapshot(
            backend_name=snapshot["backend_name"],
            runtime_engine=snapshot["runtime_engine"],
            runtime_engine_version=snapshot["runtime_engine_version"],
            model_name=snapshot["model_name"],
            model_manifest_hash=snapshot.get("model_manifest_hash"),
            runtime_config_json=snapshot["runtime_config_json"],
            tokenizer_info_json=snapshot["tokenizer_info_json"],
            snapshot_hash=snapshot["snapshot_hash"],
        )
        session.add(existing_snapshot)
        await session.flush()

    prompt_source = _extract_prompt_text(request_payload)
    response_source = _extract_response_text(response_payload)
    chat_template_hash = snapshot["tokenizer_info_json"].get("template_hash")
    capture_prompt_hash_only = getattr(cfg, "commercial_replay_capture_prompt_hash_only", True)
    record_metadata = {
        **sanitized_metadata,
        "seed_source": seed_capture["seed_source"],
        "backend_supports_seed": seed_capture["backend_supports_seed"],
        "prompt_retained": not capture_prompt_hash_only,
        "response_retained": False,
        "runtime_snapshot_hash": existing_snapshot.snapshot_hash,
        "replay_notes": "best-effort reproducibility only; cross-hardware/model bit-perfect determinism is not guaranteed",
    }
    if not capture_prompt_hash_only and prompt_source:
        record_metadata["prompt_text"] = prompt_source
    if response_source:
        record_metadata["response_text"] = response_source[:4000]
    immutable_payload = {
        "request_id": request_id,
        "correlation_id": correlation_id or get_correlation_id(),
        "client_id": client_id,
        "model_name": model_name,
        "model_alias": model_alias,
        "provider": provider,
        "backend_name": backend_name,
        "prompt_hash": hash_prompt(prompt_source or request_payload or {}),
        "request_payload_hash": _sha256_payload(sanitize_report_payload(request_payload or {})),
        "response_payload_hash": _sha256_payload(sanitize_report_payload(response_payload or {})),
        "snapshot_hash": existing_snapshot.snapshot_hash,
        "metadata": sanitize_report_payload({k: v for k, v in record_metadata.items() if k not in {"prompt_text", "response_text"}}),
    }
    record = CommercialInferenceReproducibilityRecord(
        request_id=request_id,
        correlation_id=correlation_id or get_correlation_id() or None,
        client_id=client_id,
        model_name=model_name,
        model_alias=model_alias,
        provider=provider,
        backend_name=backend_name,
        tokenizer_name=snapshot["tokenizer_info_json"].get("tokenizer_name"),
        tokenizer_version=snapshot["tokenizer_info_json"].get("tokenizer_version"),
        chat_template_hash=chat_template_hash,
        prompt_hash=immutable_payload["prompt_hash"],
        request_payload_hash=immutable_payload["request_payload_hash"],
        response_payload_hash=immutable_payload["response_payload_hash"],
        seed=seed_capture["seed"],
        temperature=request_payload.get("temperature") if request_payload else None,
        top_p=request_payload.get("top_p") if request_payload else None,
        top_k=request_payload.get("top_k") if request_payload else None,
        min_p=request_payload.get("min_p") if request_payload else None,
        repetition_penalty=request_payload.get("repetition_penalty") if request_payload else request_payload.get("repeat_penalty") if request_payload else None,
        max_tokens=request_payload.get("max_tokens") if request_payload else None,
        runtime_engine=snapshot["runtime_engine"],
        runtime_engine_version=snapshot["runtime_engine_version"],
        model_manifest_hash=registry_entry.manifest_hash if registry_entry else None,
        model_checksum=registry_entry.checksum_sha256 if registry_entry else None,
        runtime_config_hash=existing_snapshot.snapshot_hash,
        replay_supported=bool(seed_capture["replay_supported"] and response_payload),
        replay_status=replay_status,
        immutable_hash=_sha256_payload(immutable_payload),
        metadata_json=record_metadata,
    )
    session.add(record)
    await session.flush()
    return record
