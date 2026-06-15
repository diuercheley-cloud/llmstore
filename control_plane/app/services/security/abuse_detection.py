from __future__ import annotations

import hashlib
import json
import logging
import uuid

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.core.abuse_action import AbuseAction
from app.models.core.abuse_event import AbuseEvent
from app.models.core.client import Client
from redis.asyncio import Redis
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

ABUSE_SIGNALS = {
    "requests_per_minute_above_plan": {"severity": "medium", "window": 60},
    "tokens_per_minute_above_plan": {"severity": "medium", "window": 60},
    "repeated_auth_errors": {"severity": "high", "window": 300},
    "repeated_giant_prompts": {"severity": "medium", "window": 900},
    "request_loop": {"severity": "low", "window": 600},
    "high_cache_miss_repetitive": {"severity": "low", "window": 600},
    "cloud_without_balance": {"severity": "high", "window": 60},
    "high_estimated_cost": {"severity": "high", "window": 300},
    "repeated_streaming_abort": {"severity": "low", "window": 300},
    "excessive_rag_upload": {"severity": "medium", "window": 300},
    "excessive_tts_chars": {"severity": "medium", "window": 300},
}

SIGNAL_THRESHOLDS = {
    "requests_per_minute_above_plan": {"count": 1, "description": "requests/min > plan limit"},
    "tokens_per_minute_above_plan": {"count": 1, "description": "tokens/min > plan quota"},
    "repeated_auth_errors": {"count": 5, "description": "5+ auth errors in 5min"},
    "repeated_giant_prompts": {"count": 3, "description": "3+ same giant prompt in 15min"},
    "request_loop": {"count": 5, "description": "5+ exact same request in 10min"},
    "high_cache_miss_repetitive": {"count": 10, "description": "10+ cache misses, repetitive"},
    "cloud_without_balance": {"count": 1, "description": "cloud request with <= 0 balance"},
    "high_estimated_cost": {"count": 1, "description": "cost spike above threshold"},
    "repeated_streaming_abort": {"count": 3, "description": "3+ stream aborts in 5min"},
    "excessive_rag_upload": {"count": 5, "description": "5+ RAG uploads in 5min"},
    "excessive_tts_chars": {"count": 1, "description": "TTS chars above plan limit"},
}

COST_SPIKE_THRESHOLD_BRL = 5.0
GIANT_PROMPT_TOKENS = 2048
CACHE_MISS_RATIO_THRESHOLD = 0.8


def _is_enabled() -> bool:
    return get_settings().abuse_detection_enabled


def _is_dry_run() -> bool:
    return get_settings().abuse_dry_run


def _auto_suspend_enabled() -> bool:
    return get_settings().abuse_auto_suspend_enabled


def _request_fingerprint(payload: dict | None) -> str | None:
    if not payload:
        return None
    messages = payload.get("messages", [])
    if not messages:
        return None
    normalized = json.dumps(messages, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def _determine_action(signal: str, severity: str, client_id: uuid.UUID | None) -> str:
    if severity == "high" and _auto_suspend_enabled() and not _is_dry_run():
        return "suspend_client"
    if severity == "high":
        return "warn"
    if severity == "medium":
        return "warn"
    return "log_only"


def _serialize_event(event: AbuseEvent) -> dict:
    details = {}
    if event.detail_json:
        try:
            details = json.loads(event.detail_json)
        except json.JSONDecodeError:
            details = {"raw": event.detail_json}
    return {
        "id": str(event.id),
        "client_id": str(event.client_id) if event.client_id else None,
        "api_key_prefix": event.api_key_prefix,
        "signal": event.signal,
        "severity": event.severity,
        "title": event.title,
        "details": details,
        "source_ip": event.source_ip,
        "correlation_id": event.correlation_id,
        "endpoint": event.endpoint,
        "estimated_cost_brl": event.estimated_cost_brl,
        "action_taken": event.action_taken,
        "dry_run": event.dry_run,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def _serialize_action(action: AbuseAction) -> dict:
    details = {}
    if action.detail_json:
        try:
            details = json.loads(action.detail_json)
        except json.JSONDecodeError:
            details = {"raw": action.detail_json}
    return {
        "id": str(action.id),
        "abuse_event_id": str(action.abuse_event_id) if action.abuse_event_id else None,
        "client_id": str(action.client_id) if action.client_id else None,
        "action": action.action,
        "reason": action.reason,
        "details": details,
        "acknowledged": action.acknowledged,
        "acknowledged_at": action.acknowledged_at.isoformat() if action.acknowledged_at else None,
        "acknowledged_by": action.acknowledged_by,
        "dry_run": action.dry_run,
        "auto_suspend": action.auto_suspend,
        "revoked": action.revoked,
        "created_at": action.created_at.isoformat() if action.created_at else None,
    }


async def record_abuse_event(
    session: AsyncSession,
    redis: Redis,
    *,
    signal: str,
    title: str,
    client_id: uuid.UUID | None = None,
    api_key_prefix: str | None = None,
    source_ip: str | None = None,
    correlation_id: str | None = None,
    endpoint: str | None = None,
    estimated_cost_brl: float | None = None,
    details: dict | None = None,
) -> tuple[AbuseEvent | None, str | None]:
    if not _is_enabled():
        return None, None

    signal_config = ABUSE_SIGNALS.get(signal)
    if not signal_config:
        logger.warning("unknown abuse signal: %s", signal)
        return None, None

    severity = signal_config["severity"]
    dry_run = _is_dry_run()
    action = await _determine_action(signal, severity, client_id)

    event = AbuseEvent(
        client_id=client_id,
        api_key_prefix=api_key_prefix,
        signal=signal,
        severity=severity,
        title=title,
        detail_json=json.dumps(details, ensure_ascii=True) if details else None,
        source_ip=source_ip,
        correlation_id=correlation_id,
        endpoint=endpoint,
        estimated_cost_brl=estimated_cost_brl,
        action_taken=action,
        dry_run=dry_run,
    )
    session.add(event)
    await session.flush()

    action_obj = AbuseAction(
        abuse_event_id=event.id,
        client_id=client_id,
        action=action,
        reason=title,
        detail_json=json.dumps(details, ensure_ascii=True) if details else None,
        dry_run=dry_run,
        auto_suspend=(action == "suspend_client"),
    )
    session.add(action_obj)

    logger.warning(
        "abuse event: signal=%s severity=%s action=%s dry_run=%s client=%s",
        signal,
        severity,
        action,
        dry_run,
        str(client_id) if client_id else None,
    )

    if action == "suspend_client" and client_id and not dry_run:
        client = await session.get(Client, client_id)
        if client:
            client.is_blocked = True
            client.updated_at = utc_now()

    await session.commit()
    return event, action


async def check_rate_limit_abuse(
    session: AsyncSession,
    redis: Redis,
    *,
    client_id: uuid.UUID,
    limit_per_minute: int,
    current_count: int,
    api_key_prefix: str | None = None,
    source_ip: str | None = None,
) -> str | None:
    if not _is_enabled():
        return None
    if current_count <= limit_per_minute:
        return None

    gate_key = f"abuse:rpm:{client_id}:gate"
    gate_set = await redis.set(gate_key, "1", ex=60, nx=True)
    if not gate_set:
        return None

    event, action = await record_abuse_event(
        session,
        redis,
        signal="requests_per_minute_above_plan",
        title=f"Requests/min ({current_count}) above plan limit ({limit_per_minute})",
        client_id=client_id,
        api_key_prefix=api_key_prefix,
        source_ip=source_ip,
        endpoint="rate_limit",
        details={"current_count": current_count, "limit": limit_per_minute},
    )
    return action


async def check_token_abuse(
    session: AsyncSession,
    redis: Redis,
    *,
    client_id: uuid.UUID,
    tokens_used: int,
    daily_limit: int,
    api_key_prefix: str | None = None,
    source_ip: str | None = None,
) -> str | None:
    if not _is_enabled():
        return None
    daily_ratio = tokens_used / daily_limit if daily_limit else 0
    if daily_ratio < 1.0:
        return None

    gate_key = f"abuse:tokens:{client_id}:gate"
    gate_set = await redis.set(gate_key, "1", ex=60, nx=True)
    if not gate_set:
        return None

    event, action = await record_abuse_event(
        session,
        redis,
        signal="tokens_per_minute_above_plan",
        title=f"Token usage ({tokens_used}) at {daily_ratio:.1%} of daily limit ({daily_limit})",
        client_id=client_id,
        api_key_prefix=api_key_prefix,
        source_ip=source_ip,
        endpoint="token_quota",
        details={
            "tokens_used": tokens_used,
            "daily_limit": daily_limit,
            "ratio": round(daily_ratio, 4),
        },
    )
    return action


async def check_auth_error_burst(
    session: AsyncSession,
    redis: Redis,
    *,
    client_id: uuid.UUID | None = None,
    source_ip: str,
    api_key_prefix: str | None = None,
) -> str | None:
    if not _is_enabled():
        return None

    counter_key = f"abuse:auth-errors:{source_ip}"
    total = await redis.incr(counter_key)
    if total == 1:
        await redis.expire(counter_key, 300)
    if total < SIGNAL_THRESHOLDS["repeated_auth_errors"]["count"]:
        return None

    gate_key = f"abuse:auth-errors:{source_ip}:gate:{total}"
    gate_set = await redis.set(gate_key, "1", ex=300, nx=True)
    if not gate_set:
        return None

    event, action = await record_abuse_event(
        session,
        redis,
        signal="repeated_auth_errors",
        title=f"{total} auth errors from {source_ip}",
        client_id=client_id,
        api_key_prefix=api_key_prefix,
        source_ip=source_ip,
        endpoint="auth",
        details={"total_errors": total, "window_seconds": 300},
    )
    return action


async def check_repeated_giant_prompt(
    session: AsyncSession,
    redis: Redis,
    *,
    client_id: uuid.UUID,
    prompt_tokens: int,
    prompt_fingerprint: str,
    api_key_prefix: str | None = None,
) -> str | None:
    if not _is_enabled():
        return None
    if prompt_tokens < GIANT_PROMPT_TOKENS:
        return None

    repeat_key = f"abuse:giant-prompt:{client_id}:{prompt_fingerprint}"
    seen = await redis.incr(repeat_key)
    if seen == 1:
        await redis.expire(repeat_key, 900)
    if seen < SIGNAL_THRESHOLDS["repeated_giant_prompts"]["count"]:
        return None

    gate_key = f"abuse:giant-prompt:{client_id}:{prompt_fingerprint}:gate:{seen}"
    gate_set = await redis.set(gate_key, "1", ex=900, nx=True)
    if not gate_set:
        return None

    event, action = await record_abuse_event(
        session,
        redis,
        signal="repeated_giant_prompts",
        title=f"Large prompt ({prompt_tokens}t) repeated {seen}x",
        client_id=client_id,
        api_key_prefix=api_key_prefix,
        endpoint="chat",
        details={"prompt_tokens": prompt_tokens, "repetitions": seen},
    )
    return action


async def check_request_loop(
    session: AsyncSession,
    redis: Redis,
    *,
    client_id: uuid.UUID,
    fingerprint: str,
    api_key_prefix: str | None = None,
) -> str | None:
    if not _is_enabled():
        return None
    if not fingerprint:
        return None

    loop_key = f"abuse:request-loop:{client_id}:{fingerprint}"
    seen = await redis.incr(loop_key)
    if seen == 1:
        await redis.expire(loop_key, 600)
    if seen < SIGNAL_THRESHOLDS["request_loop"]["count"]:
        return None

    gate_key = f"abuse:request-loop:{client_id}:{fingerprint}:gate:{seen}"
    gate_set = await redis.set(gate_key, "1", ex=600, nx=True)
    if not gate_set:
        return None

    event, action = await record_abuse_event(
        session,
        redis,
        signal="request_loop",
        title=f"Same request repeated {seen}x in 10min",
        client_id=client_id,
        api_key_prefix=api_key_prefix,
        endpoint="chat",
        details={"repetitions": seen},
    )
    return action


async def check_cache_miss_abuse(
    session: AsyncSession,
    redis: Redis,
    *,
    client_id: uuid.UUID,
    cache_hits: int,
    cache_misses: int,
    api_key_prefix: str | None = None,
) -> str | None:
    if not _is_enabled():
        return None
    total = cache_hits + cache_misses
    if total < SIGNAL_THRESHOLDS["high_cache_miss_repetitive"]["count"]:
        return None
    miss_ratio = cache_misses / total if total else 0
    if miss_ratio < CACHE_MISS_RATIO_THRESHOLD:
        return None

    gate_key = f"abuse:cache-miss:{client_id}:gate"
    gate_set = await redis.set(gate_key, "1", ex=600, nx=True)
    if not gate_set:
        return None

    event, action = await record_abuse_event(
        session,
        redis,
        signal="high_cache_miss_repetitive",
        title=f"High cache miss ratio ({miss_ratio:.0%}) with repetitive pattern",
        client_id=client_id,
        api_key_prefix=api_key_prefix,
        endpoint="cache",
        details={
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "miss_ratio": round(miss_ratio, 4),
        },
    )
    return action


async def check_cloud_without_balance(
    session: AsyncSession,
    redis: Redis,
    *,
    client_id: uuid.UUID,
    wallet_balance_brl: float,
    api_key_prefix: str | None = None,
) -> str | None:
    if not _is_enabled():
        return None
    if wallet_balance_brl > 0:
        return None

    gate_key = f"abuse:cloud-nobalance:{client_id}:gate"
    gate_set = await redis.set(gate_key, "1", ex=60, nx=True)
    if not gate_set:
        return None

    event, action = await record_abuse_event(
        session,
        redis,
        signal="cloud_without_balance",
        title="Cloud request attempted with insufficient wallet balance",
        client_id=client_id,
        api_key_prefix=api_key_prefix,
        endpoint="cloud_provider",
        details={"wallet_balance_brl": wallet_balance_brl},
    )
    return action


async def check_cost_spike(
    session: AsyncSession,
    redis: Redis,
    *,
    client_id: uuid.UUID,
    recent_cost_brl: float,
    api_key_prefix: str | None = None,
) -> str | None:
    if not _is_enabled():
        return None
    if recent_cost_brl < COST_SPIKE_THRESHOLD_BRL:
        return None

    gate_key = f"abuse:cost-spike:{client_id}:gate"
    gate_set = await redis.set(gate_key, "1", ex=300, nx=True)
    if not gate_set:
        return None

    event, action = await record_abuse_event(
        session,
        redis,
        signal="high_estimated_cost",
        title=f"Estimated cost spike: BRL {recent_cost_brl:.2f} in short period",
        client_id=client_id,
        api_key_prefix=api_key_prefix,
        estimated_cost_brl=recent_cost_brl,
        endpoint="cost",
        details={"recent_cost_brl": round(recent_cost_brl, 2)},
    )
    return action


async def check_streaming_abort(
    session: AsyncSession,
    redis: Redis,
    *,
    client_id: uuid.UUID,
    api_key_prefix: str | None = None,
) -> str | None:
    if not _is_enabled():
        return None

    abort_key = f"abuse:stream-abort:{client_id}"
    total = await redis.incr(abort_key)
    if total == 1:
        await redis.expire(abort_key, 300)
    if total < SIGNAL_THRESHOLDS["repeated_streaming_abort"]["count"]:
        return None

    gate_key = f"abuse:stream-abort:{client_id}:gate:{total}"
    gate_set = await redis.set(gate_key, "1", ex=300, nx=True)
    if not gate_set:
        return None

    event, action = await record_abuse_event(
        session,
        redis,
        signal="repeated_streaming_abort",
        title=f"Streaming aborted {total}x in 5min",
        client_id=client_id,
        api_key_prefix=api_key_prefix,
        endpoint="chat/stream",
        details={"total_aborts": total},
    )
    return action


async def check_rag_upload_abuse(
    session: AsyncSession,
    redis: Redis,
    *,
    client_id: uuid.UUID,
    api_key_prefix: str | None = None,
) -> str | None:
    if not _is_enabled():
        return None

    upload_key = f"abuse:rag-upload:{client_id}"
    total = await redis.incr(upload_key)
    if total == 1:
        await redis.expire(upload_key, 300)
    if total < SIGNAL_THRESHOLDS["excessive_rag_upload"]["count"]:
        return None

    gate_key = f"abuse:rag-upload:{client_id}:gate:{total}"
    gate_set = await redis.set(gate_key, "1", ex=300, nx=True)
    if not gate_set:
        return None

    event, action = await record_abuse_event(
        session,
        redis,
        signal="excessive_rag_upload",
        title=f"RAG upload burst: {total} uploads in 5min",
        client_id=client_id,
        api_key_prefix=api_key_prefix,
        endpoint="rag/upload",
        details={"total_uploads": total, "window_seconds": 300},
    )
    return action


async def check_tts_abuse(
    session: AsyncSession,
    redis: Redis,
    *,
    client_id: uuid.UUID,
    chars_total: int,
    monthly_limit: int,
    api_key_prefix: str | None = None,
) -> str | None:
    if not _is_enabled():
        return None
    if chars_total <= monthly_limit:
        return None

    gate_key = f"abuse:tts:{client_id}:gate"
    gate_set = await redis.set(gate_key, "1", ex=60, nx=True)
    if not gate_set:
        return None

    event, action = await record_abuse_event(
        session,
        redis,
        signal="excessive_tts_chars",
        title=f"TTS chars ({chars_total}) above monthly limit ({monthly_limit})",
        client_id=client_id,
        api_key_prefix=api_key_prefix,
        endpoint="tts",
        details={"chars_total": chars_total, "monthly_limit": monthly_limit},
    )
    return action


async def list_abuse_events(
    session: AsyncSession,
    limit: int = 200,
    signal: str | None = None,
    client_id: uuid.UUID | None = None,
    severity: str | None = None,
) -> list[dict]:
    stmt = select(AbuseEvent).order_by(desc(AbuseEvent.created_at))
    if signal:
        stmt = stmt.where(AbuseEvent.signal == signal)
    if client_id:
        stmt = stmt.where(AbuseEvent.client_id == client_id)
    if severity:
        stmt = stmt.where(AbuseEvent.severity == severity)
    stmt = stmt.limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_serialize_event(row) for row in rows]


async def get_abuse_summary(session: AsyncSession) -> dict:
    total = await session.execute(select(func.count(AbuseEvent.id)))
    total_count = total.scalar() or 0

    by_signal = await session.execute(
        select(AbuseEvent.signal, func.count(AbuseEvent.id))
        .group_by(AbuseEvent.signal)
        .order_by(func.count(AbuseEvent.id).desc())
    )

    by_severity = await session.execute(
        select(AbuseEvent.severity, func.count(AbuseEvent.id))
        .group_by(AbuseEvent.severity)
        .order_by(func.count(AbuseEvent.id).desc())
    )

    unacknowledged = await session.execute(
        select(func.count(AbuseAction.id)).where(AbuseAction.acknowledged == False)
    )

    actions_taken = await session.execute(
        select(AbuseAction.action, func.count(AbuseAction.id))
        .group_by(AbuseAction.action)
        .order_by(func.count(AbuseAction.id).desc())
    )

    return {
        "total_events": total_count,
        "by_signal": {row[0]: row[1] for row in by_signal.all()},
        "by_severity": {row[0]: row[1] for row in by_severity.all()},
        "unacknowledged_actions": unacknowledged.scalar() or 0,
        "actions_taken": {row[0]: row[1] for row in actions_taken.all()},
        "dry_run": _is_dry_run(),
        "auto_suspend_enabled": _auto_suspend_enabled(),
        "detection_enabled": _is_enabled(),
    }


async def acknowledge_action(
    session: AsyncSession,
    action_id: uuid.UUID,
    acknowledged_by: str | None = None,
) -> dict | None:
    action = await session.get(AbuseAction, action_id)
    if not action:
        return None
    action.acknowledged = True
    action.acknowledged_at = utc_now()
    action.acknowledged_by = acknowledged_by
    await session.commit()
    return _serialize_action(action)


async def suspend_client(
    session: AsyncSession,
    client_id: uuid.UUID,
    reason: str = "manual admin action",
) -> dict | None:
    client = await session.get(Client, client_id)
    if not client:
        return None
    client.is_blocked = True
    client.updated_at = utc_now()

    action = AbuseAction(
        client_id=client_id,
        action="suspend_client",
        reason=reason,
        detail_json=json.dumps({"manual": True, "reason": reason}, ensure_ascii=True),
        dry_run=False,
        auto_suspend=False,
    )
    session.add(action)
    await session.commit()
    return {"client_id": str(client_id), "action": "suspend_client", "reason": reason}


async def unsuspend_client(
    session: AsyncSession,
    client_id: uuid.UUID,
    reason: str = "manual admin action",
) -> dict | None:
    client = await session.get(Client, client_id)
    if not client:
        return None
    client.is_blocked = False
    client.updated_at = utc_now()

    action = AbuseAction(
        client_id=client_id,
        action="unsuspend",
        reason=reason,
        detail_json=json.dumps({"manual": True, "reason": reason}, ensure_ascii=True),
        dry_run=False,
        auto_suspend=False,
    )
    session.add(action)
    await session.commit()
    return {"client_id": str(client_id), "action": "unsuspend", "reason": reason}
