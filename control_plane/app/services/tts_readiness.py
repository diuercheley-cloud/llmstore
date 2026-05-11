from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable


HttpRequest = Callable[..., tuple[int | None, str, dict[str, str], str | None]]


@dataclass
class TtsReadinessClient:
    ok: bool
    detail: str
    client_id: str | None = None
    client_name: str | None = None
    plan_id: str | None = None
    plan_code: str | None = None
    api_key: str | None = None
    key_prefix: str | None = None
    temporary: bool = False


@dataclass
class TtsProbeAssessment:
    status: str
    details: str
    remediation: str
    optional: bool = False
    generated_output: bool = False


def redact_api_key(value: str | None) -> str:
    if not value:
        return "missing"
    if len(value) <= 10:
        return "[redacted]"
    return f"{value[:6]}...[redacted]...{value[-4:]}"


def build_tts_probe_skip(skip_reason: str) -> TtsProbeAssessment:
    return TtsProbeAssessment(
        status="skip",
        details=skip_reason,
        remediation="Mantenha a checagem opcional; só execute o probe autenticado quando TTS estiver habilitado.",
        optional=True,
        generated_output=False,
    )


def response_contains_audio(headers: dict[str, str] | None, body: bytes) -> bool:
    content_type = ""
    if headers:
        content_type = next(
            (value for key, value in headers.items() if key.lower() == "content-type"),
            "",
        )
    content_type = content_type.lower()
    if "audio/" in content_type or "application/octet-stream" in content_type:
        return bool(body)
    return body.startswith(b"RIFF") or body.startswith(b"ID3") or body.startswith(b"OggS")


def response_contains_generated_payload(headers: dict[str, str] | None, body: bytes) -> bool:
    if response_contains_audio(headers, body):
        return True
    if not body:
        return False
    content_type = ""
    if headers:
        content_type = next(
            (value for key, value in headers.items() if key.lower() == "content-type"),
            "",
        )
    content_type = content_type.lower()
    if "json" not in content_type and not body[:1] in {b"{", b"["}:
        return False
    try:
        payload = json.loads(body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return False
    if isinstance(payload, dict):
        interesting_keys = {
            "audio",
            "audio_base64",
            "audio_file",
            "audio_file_id",
            "bytes",
            "content",
            "file",
            "file_id",
            "path",
            "url",
        }
        return any(key in payload and payload[key] for key in interesting_keys)
    return False


def assess_tts_probe(
    *,
    tts_enabled: bool,
    http_status: int | None,
    headers: dict[str, str] | None,
    body: bytes,
    usage_recorded: bool,
    client_detail: str,
) -> TtsProbeAssessment:
    if not tts_enabled:
        return build_tts_probe_skip("TTS desabilitado via TTS_ENABLED=false.")

    generated_output = response_contains_generated_payload(headers, body)
    content_type = ""
    if headers:
        content_type = next(
            (value for key, value in headers.items() if key.lower() == "content-type"),
            "",
        )

    if http_status in {200, 201} and generated_output and usage_recorded:
        return TtsProbeAssessment(
            status="pass",
            details=f"HTTP {http_status}; content-type={content_type or 'n/a'}; usage registrado; client={client_detail}",
            remediation="Nenhuma ação necessária.",
            generated_output=True,
        )
    if http_status == 401:
        return TtsProbeAssessment(
            status="fail",
            details=f"HTTP 401 no probe TTS autenticado; client={client_detail}",
            remediation="Bearer inválido ou expirado no probe. Gere uma nova API key do cliente readiness com plano TTS habilitado e valide o header Authorization.",
            generated_output=False,
        )
    if http_status == 402:
        return TtsProbeAssessment(
            status="fail",
            details=f"HTTP 402 no probe TTS autenticado; client={client_detail}",
            remediation="O cliente usado no probe está suspenso por billing. Reative-o ou crie um cliente readiness ativo; cliente suspenso deve continuar bloqueado.",
            generated_output=False,
        )
    if http_status == 403:
        return TtsProbeAssessment(
            status="fail",
            details=f"HTTP 403 no probe TTS autenticado; client={client_detail}",
            remediation="O cliente do probe não tem permissão para TTS ou está bloqueado. Garanta billing plan com tts_enabled=true e cliente ativo/não bloqueado.",
            generated_output=False,
        )
    if http_status in {200, 201} and not generated_output:
        return TtsProbeAssessment(
            status="fail",
            details=f"HTTP {http_status}; resposta sem áudio/payload utilizável; content-type={content_type or 'n/a'}; client={client_detail}",
            remediation="Valide o endpoint /pocket-tts/tts e o formato de resposta esperado do backend TTS.",
            generated_output=False,
        )
    if http_status in {200, 201} and not usage_recorded:
        return TtsProbeAssessment(
            status="fail",
            details=f"HTTP {http_status}; áudio gerado sem registro de usage; client={client_detail}",
            remediation="Ajuste o proxy TTS para registrar usage após respostas 200/201 bem-sucedidas.",
            generated_output=generated_output,
        )
    return TtsProbeAssessment(
        status="fail",
        details=f"HTTP {http_status if http_status is not None else 'n/a'}; content-type={content_type or 'n/a'}; client={client_detail}",
        remediation="Valide a rota /pocket-tts/tts, a autenticação Bearer e a disponibilidade do serviço Pocket TTS.",
        generated_output=generated_output,
    )


def get_or_create_tts_readiness_client(
    http_request: HttpRequest,
    admin_token: str,
    *,
    client_name: str = "tts-readiness-probe-client",
) -> TtsReadinessClient:
    if not admin_token:
        return TtsReadinessClient(ok=False, detail="admin token missing")

    auth_headers = {"X-Admin-Token": admin_token}
    status, body, _, error = http_request("/admin/billing/plans", headers=auth_headers)
    if status != 200:
        return TtsReadinessClient(ok=False, detail=f"failed to list billing plans: {error or body[:160]}")
    try:
        plans = json.loads(body)
    except json.JSONDecodeError:
        return TtsReadinessClient(ok=False, detail="invalid billing plans payload")
    tts_plan = next((plan for plan in plans if plan.get("tts_enabled") and plan.get("is_active", True)), None)
    if not tts_plan:
        return TtsReadinessClient(ok=False, detail="no active billing plan with tts_enabled=true")

    status, body, _, error = http_request("/admin/clients", headers=auth_headers)
    if status != 200:
        return TtsReadinessClient(ok=False, detail=f"failed to list clients: {error or body[:160]}")
    try:
        clients = json.loads(body)
    except json.JSONDecodeError:
        return TtsReadinessClient(ok=False, detail="invalid clients payload")

    reusable = next(
        (
            client
            for client in clients
            if client.get("name") == client_name
            and not client.get("is_blocked")
            and client.get("billing_status") == "active"
        ),
        None,
    )

    temporary = False
    if reusable:
        client = reusable
    else:
        suffix = int(time.time())
        desired_name = f"{client_name}-{suffix}"
        payload = {
            "name": desired_name,
            "description": "temporary client for authenticated TTS readiness probe",
            "billing_plan_id": tts_plan["id"],
            "rate_limit_per_minute": 10,
        }
        status, body, _, error = http_request(
            "/admin/clients",
            method="POST",
            headers={**auth_headers, "Content-Type": "application/json"},
            body=json.dumps(payload).encode("utf-8"),
        )
        if status != 201:
            return TtsReadinessClient(ok=False, detail=f"tts readiness client creation failed: {error or body[:160]}")
        try:
            client = json.loads(body)
        except json.JSONDecodeError:
            return TtsReadinessClient(ok=False, detail="invalid client creation payload")
        temporary = True

    if client.get("billing_plan_id") != tts_plan["id"]:
        status, body, _, error = http_request(
            f"/admin/clients/{client['id']}/billing-plan",
            method="PATCH",
            headers={**auth_headers, "Content-Type": "application/json"},
            body=json.dumps({"billing_plan_id": tts_plan["id"]}).encode("utf-8"),
        )
        if status != 200:
            return TtsReadinessClient(ok=False, detail=f"failed to attach tts-enabled plan: {error or body[:160]}")
        try:
            client = json.loads(body)
        except json.JSONDecodeError:
            return TtsReadinessClient(ok=False, detail="invalid billing-plan patch payload")

    key_payload = {
        "client_id": client["id"],
        "name": f"tts-readiness-{int(time.time())}",
    }
    status, body, _, error = http_request(
        "/admin/api-keys",
        method="POST",
        headers={**auth_headers, "Content-Type": "application/json"},
        body=json.dumps(key_payload).encode("utf-8"),
    )
    if status != 201:
        return TtsReadinessClient(ok=False, detail=f"failed to issue tts api key: {error or body[:160]}")
    try:
        key_data = json.loads(body)
    except json.JSONDecodeError:
        return TtsReadinessClient(ok=False, detail="invalid api key creation payload")

    return TtsReadinessClient(
        ok=True,
        detail=f"client={client.get('name')} plan={tts_plan.get('code')} key={redact_api_key(key_data.get('api_key'))}",
        client_id=client.get("id"),
        client_name=client.get("name"),
        plan_id=tts_plan.get("id"),
        plan_code=tts_plan.get("code"),
        api_key=key_data.get("api_key"),
        key_prefix=key_data.get("key_prefix"),
        temporary=temporary,
    )
