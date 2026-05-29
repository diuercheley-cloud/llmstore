from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class TTSProbeResult:
    status: str
    optional: bool
    details: str
    remediation: str = ""


@dataclass
class TTSReadinessClient:
    ok: bool
    client_id: str
    plan_code: str
    temporary: bool
    detail: str
    api_key: str | None = None


def build_tts_probe_skip(details: str) -> TTSProbeResult:
    return TTSProbeResult(status="skip", optional=True, details=details)


def assess_tts_probe(
    *,
    tts_enabled: bool,
    http_status: int,
    headers: dict[str, str] | None,
    body: bytes,
    usage_recorded: bool,
    client_detail: str,
) -> TTSProbeResult:
    if not tts_enabled:
        return build_tts_probe_skip("TTS desabilitado via TTS_ENABLED=false.")

    if http_status == 401:
        return TTSProbeResult(
            status="fail",
            optional=False,
            details=client_detail,
            remediation="Bearer inválido; gere uma nova API key com TTS habilitado e repita o probe.",
        )

    if 200 <= http_status < 300 and usage_recorded:
        return TTSProbeResult(status="pass", optional=False, details=client_detail)

    return TTSProbeResult(
        status="fail",
        optional=False,
        details=client_detail,
        remediation="Verifique a rota de TTS, o plano do cliente e o registro de uso.",
    )


def get_or_create_tts_readiness_client(
    http_request: Callable[..., tuple[int, Any, dict[str, str], Any]],
    admin_token: str,
) -> TTSReadinessClient:
    status, plans_body, _, _ = http_request("/admin/billing/plans", method="GET")
    if status != 200:
        return TTSReadinessClient(False, "", "", False, "billing plans unavailable")

    import json

    plans = json.loads(plans_body)
    tts_plan = next((plan for plan in plans if plan.get("tts_enabled") and plan.get("is_active", True)), None)
    if not tts_plan:
        return TTSReadinessClient(False, "", "", False, "no active TTS plan")

    status, clients_body, _, _ = http_request("/admin/clients", method="GET")
    if status != 200:
        return TTSReadinessClient(False, "", "", False, "clients unavailable")

    clients = json.loads(clients_body)
    active_client = next(
        (
            client
            for client in clients
            if client.get("billing_status") != "suspended"
            and not client.get("is_blocked")
            and client.get("billing_plan_id") == tts_plan["id"]
        ),
        None,
    )

    temporary = False
    if active_client:
        client_id = active_client["id"]
        client_name = active_client["name"]
    else:
        temporary = True
        candidate_name = f"tts-readiness-probe-client-{len(clients) + 1}"
        status, client_body, _, _ = http_request(
            "/admin/clients",
            method="POST",
            body={"name": candidate_name, "billing_plan_id": tts_plan["id"]},
        )
        if status not in (200, 201):
            return TTSReadinessClient(False, "", "", False, "client creation failed")
        client_payload = json.loads(client_body)
        client_id = client_payload["id"]
        client_name = client_payload["name"]

    status, key_body, _, _ = http_request(
        "/admin/api-keys",
        method="POST",
        body={"client_id": client_id, "name": "tts-readiness-probe"},
    )
    if status not in (200, 201):
        return TTSReadinessClient(False, client_id, tts_plan["code"], temporary, "api key creation failed")
    key_payload = json.loads(key_body)
    key_prefix = key_payload.get("key_prefix", "sk-redacted")

    return TTSReadinessClient(
        ok=True,
        client_id=client_id,
        plan_code=tts_plan["code"],
        temporary=temporary,
        detail=f"client={client_name} key={key_prefix}[redacted]",
        api_key=key_payload.get("api_key"),
    )
