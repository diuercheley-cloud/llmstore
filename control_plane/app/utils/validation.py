import json

from app.core.config import get_settings
from app.models.core.client import Client
from app.services.billing import resolve_effective_plan
from app.services.billing.core import resolve_effective_plan_for_session
from fastapi import HTTPException

settings = get_settings()


def validate_params(client: Client, payload):
    effective_plan = resolve_effective_plan(client)

    # Load client defaults from metadata_json if available
    client_defaults = {}
    if client.metadata_json:
        try:
            client_defaults = json.loads(client.metadata_json)
        except Exception:
            pass

    requested_max_tokens = (
        payload.max_tokens or client_defaults.get("max_tokens") or settings.default_max_tokens
    )

    limit = min(effective_plan.max_output_tokens, settings.inference_max_completion_tokens)
    if requested_max_tokens > limit:
        # Cap instead of raising, as requested for optimization
        max_tokens = limit
    else:
        max_tokens = requested_max_tokens

    temperature = payload.temperature
    if temperature is None:
        temperature = client_defaults.get("temperature")
    if temperature is None:
        temperature = settings.default_temperature

    top_p = payload.top_p
    if top_p is None:
        top_p = client_defaults.get("top_p")
    if top_p is None:
        top_p = settings.default_top_p

    if getattr(payload, "stream", False) and not effective_plan.allow_streaming:
        raise HTTPException(
            status_code=403, detail="streaming is not allowed for this billing plan"
        )

    # Feature Gates
    if (
        not effective_plan.responses_enabled
        and getattr(payload, "_endpoint", "") == "/v1/responses"
    ):
        raise HTTPException(
            status_code=403, detail="responses feature is not enabled for your plan"
        )

    if temperature > settings.max_temperature:
        raise HTTPException(status_code=422, detail="temperature exceeds configured maximum")
    if top_p > settings.max_top_p:
        raise HTTPException(status_code=422, detail="top_p exceeds configured maximum")
    return max_tokens, temperature, top_p, effective_plan


async def validate_params_for_session(session, client: Client, payload):
    effective_plan = await resolve_effective_plan_for_session(session, client)

    client_defaults = {}
    if client.metadata_json:
        try:
            client_defaults = json.loads(client.metadata_json)
        except Exception:
            pass

    requested_max_tokens = (
        payload.max_tokens or client_defaults.get("max_tokens") or settings.default_max_tokens
    )
    limit = min(effective_plan.max_output_tokens, settings.inference_max_completion_tokens)
    max_tokens = limit if requested_max_tokens > limit else requested_max_tokens

    temperature = payload.temperature
    if temperature is None:
        temperature = client_defaults.get("temperature")
    if temperature is None:
        temperature = settings.default_temperature

    top_p = payload.top_p
    if top_p is None:
        top_p = client_defaults.get("top_p")
    if top_p is None:
        top_p = settings.default_top_p

    if getattr(payload, "stream", False) and not effective_plan.allow_streaming:
        raise HTTPException(
            status_code=403, detail="streaming is not allowed for this billing plan"
        )
    if (
        not effective_plan.responses_enabled
        and getattr(payload, "_endpoint", "") == "/v1/responses"
    ):
        raise HTTPException(
            status_code=403, detail="responses feature is not enabled for your plan"
        )
    if temperature > settings.max_temperature:
        raise HTTPException(status_code=422, detail="temperature exceeds configured maximum")
    if top_p > settings.max_top_p:
        raise HTTPException(status_code=422, detail="top_p exceeds configured maximum")
    return max_tokens, temperature, top_p, effective_plan


def normalize_messages(messages: list[dict]) -> list[dict]:
    normalized = []
    for msg in messages:
        content = msg.get("content")
        if content is None:
            msg["content"] = ""
            normalized.append(msg)
            continue
        if isinstance(content, list):
            text_parts = []
            for part in content:
                part_type = part.get("type")
                if part_type == "text":
                    text_parts.append(part.get("text") or "")
                elif part_type == "image_url":
                    raise HTTPException(
                        status_code=422,
                        detail="image_url is not supported yet. Only text content parts are allowed.",
                    )
            msg["content"] = "\n".join(text_parts)
        normalized.append(msg)
    return normalized
