#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
export BASE_URL

python3 <<'PY'
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(os.getcwd())
sys.path.insert(0, str(ROOT / "control_plane"))

from app.services.tts_readiness import assess_tts_probe, get_or_create_tts_readiness_client

BASE_URL = os.environ["BASE_URL"].rstrip("/")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
TTS_ENABLED = os.environ.get("TTS_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def http_request(
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: int = 20,
) -> tuple[int | None, str, dict[str, str], str | None]:
    url = path if path.startswith("http://") or path.startswith("https://") else f"{BASE_URL}{path}"
    request = urllib.request.Request(url, method=method, data=body)
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace"), dict(response.headers.items()), None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace"), dict(exc.headers.items()), None
    except Exception as exc:  # noqa: BLE001
        return None, "", {}, str(exc)


def http_request_bytes(
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: int = 20,
) -> tuple[int | None, bytes, dict[str, str], str | None]:
    url = path if path.startswith("http://") or path.startswith("https://") else f"{BASE_URL}{path}"
    request = urllib.request.Request(url, method=method, data=body)
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers.items()), None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers.items()), None
    except Exception as exc:  # noqa: BLE001
        return None, b"", {}, str(exc)


def json_request(path: str, payload: dict, *, method: str = "POST", headers: dict[str, str] | None = None):
    merged_headers = {"Content-Type": "application/json"}
    merged_headers.update(headers or {})
    return http_request(path, method=method, headers=merged_headers, body=json.dumps(payload).encode("utf-8"))


def require_admin_headers() -> dict[str, str]:
    if not ADMIN_TOKEN:
        raise SystemExit("ADMIN_TOKEN is required for validate-tts-readiness-local.sh when TTS is enabled.")
    return {"X-Admin-Token": ADMIN_TOKEN}


def ensure_disabled_tts_plan() -> dict:
    status, body, _, error = http_request("/admin/billing/plans", headers=require_admin_headers())
    if status != 200:
        raise SystemExit(f"Failed to list billing plans: {error or body[:160]}")
    plans = json.loads(body)
    existing = next((plan for plan in plans if not plan.get("tts_enabled") and plan.get("is_active", True)), None)
    if existing:
        return existing
    payload = {
        "code": "tts-readiness-disabled",
        "name": "TTS Readiness Disabled",
        "description": "Validation-only plan with TTS disabled.",
        "rate_limit_per_minute": 10,
        "daily_token_quota": 1000,
        "weekly_token_quota": 5000,
        "monthly_token_quota": 10000,
        "max_output_tokens": 256,
        "allow_streaming": False,
        "tts_enabled": False,
        "tts_chars_per_month": 0,
        "responses_enabled": True,
        "is_active": True,
    }
    status, body, _, error = json_request("/admin/billing/plans", payload, headers=require_admin_headers())
    if status == 201:
        return json.loads(body)
    if status == 409:
        status, body, _, error = http_request("/admin/billing/plans", headers=require_admin_headers())
        if status == 200:
            plans = json.loads(body)
            existing = next((plan for plan in plans if plan.get("code") == payload["code"]), None)
            if existing:
                return existing
    raise SystemExit(f"Failed to provision disabled TTS plan: {error or body[:160]}")


def create_client_with_key(name: str, plan_id: str) -> tuple[str, str]:
    status, body, _, error = json_request(
        "/admin/clients",
        {"name": name, "description": "temporary readiness validation client", "billing_plan_id": plan_id},
        headers=require_admin_headers(),
    )
    if status != 201:
        raise SystemExit(f"Failed to create client {name}: {error or body[:160]}")
    client = json.loads(body)
    status, body, _, error = json_request(
        "/admin/api-keys",
        {"client_id": client["id"], "name": f"{name}-key"},
        headers=require_admin_headers(),
    )
    if status != 201:
        raise SystemExit(f"Failed to create API key for {name}: {error or body[:160]}")
    key = json.loads(body)
    return client["id"], key["api_key"]


def delete_client(client_id: str) -> None:
    if not client_id:
        return
    http_request(f"/admin/clients/{client_id}", method="DELETE", headers=require_admin_headers())


def check_usage_registered(client_id: str) -> bool:
    status, body, _, _ = http_request(f"/admin/usage/{client_id}/summary", headers=require_admin_headers())
    if status != 200:
        return False
    payload = json.loads(body)
    return int(payload.get("today", {}).get("tts_chars_used", 0)) > 0


def assert_status(label: str, actual: int | None, expected: int) -> None:
    if actual != expected:
        raise SystemExit(f"{label}: expected HTTP {expected}, got {actual}")
    print(f"{label}: PASS (HTTP {actual})")


def assert_any_status(label: str, actual: int | None, expected: set[int]) -> None:
    if actual not in expected:
        raise SystemExit(f"{label}: expected one of {sorted(expected)}, got {actual}")
    print(f"{label}: PASS (HTTP {actual})")


if not TTS_ENABLED:
    print("TTS readiness status: SKIP optional")
    print("Reason: TTS_ENABLED=false")
    raise SystemExit(0)

readiness_client = get_or_create_tts_readiness_client(http_request, ADMIN_TOKEN)
if not readiness_client.ok or not readiness_client.api_key or not readiness_client.client_id:
    raise SystemExit(f"Failed to provision TTS readiness client: {readiness_client.detail}")

temp_client_ids: list[str] = []
tmp_audio = None
run_suffix = str(int(time.time()))
try:
    status, audio_body, headers, error = http_request_bytes(
        "/pocket-tts/tts",
        method="POST",
        body=urllib.parse.urlencode({"text": "readiness tts validation"}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {readiness_client.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=60,
    )
    assessment = assess_tts_probe(
        tts_enabled=True,
        http_status=status,
        headers=headers,
        body=audio_body,
        usage_recorded=check_usage_registered(readiness_client.client_id),
        client_detail=readiness_client.detail,
    )
    if assessment.status != "pass":
        raise SystemExit(f"TTS enabled auth probe failed: {assessment.details} | remediation={assessment.remediation} | error={error}")
    tmp_audio = tempfile.NamedTemporaryFile(prefix="tts-readiness-", suffix=".wav", delete=False)
    tmp_audio.write(audio_body)
    tmp_audio.close()
    print(f"TTS enabled auth: PASS ({assessment.details})")

    disabled_plan = ensure_disabled_tts_plan()
    denied_client_id, denied_key = create_client_with_key(f"tts-readiness-denied-{run_suffix}", disabled_plan["id"])
    temp_client_ids.append(denied_client_id)
    status, _, _, _ = http_request_bytes(
        "/pocket-tts/tts",
        method="POST",
        body=urllib.parse.urlencode({"text": "should fail"}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {denied_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    assert_status("Client sem permissão TTS", status, 403)

    suspended_client_id, suspended_key = create_client_with_key(f"tts-readiness-suspended-{run_suffix}", readiness_client.plan_id)
    temp_client_ids.append(suspended_client_id)
    suspend_status, suspend_body, _, suspend_error = http_request(
        f"/admin/security/clients/{suspended_client_id}/suspend",
        method="POST",
        headers=require_admin_headers(),
    )
    if suspend_status != 200:
        raise SystemExit(f"Failed to suspend validation client: {suspend_error or suspend_body[:160]}")
    status, _, _, _ = http_request_bytes(
        "/pocket-tts/tts",
        method="POST",
        body=urllib.parse.urlencode({"text": "should be blocked"}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {suspended_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    assert_any_status("Client suspenso bloqueado", status, {402, 403})

    gitignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    if "artifacts/" not in gitignore_text and "*.wav" not in gitignore_text:
        raise SystemExit("Missing gitignore protection for generated wav files.")
    git_status = subprocess.run(
        ["git", "status", "--porcelain", "--", "*.wav"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if git_status.stdout.strip():
        raise SystemExit(f"Versionable wav files detected:\n{git_status.stdout}")
    print("WAV hygiene: PASS")

    if not check_usage_registered(readiness_client.client_id):
        raise SystemExit("TTS usage was not registered after successful generation.")
    print("Usage registration: PASS")
    print("TTS readiness status: PASS")
finally:
    if tmp_audio is not None:
        try:
            Path(tmp_audio.name).unlink(missing_ok=True)
        except OSError:
            pass
    for client_id in temp_client_ids:
        delete_client(client_id)
    if readiness_client.temporary and readiness_client.client_id:
        delete_client(readiness_client.client_id)
PY
