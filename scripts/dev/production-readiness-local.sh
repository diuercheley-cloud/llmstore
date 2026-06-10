#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env
cd "${ROOT_DIR}"

usage() {
  cat <<'EOF'
Usage: ./scripts/dev/production-readiness-local.sh [options]

Options:
  --base-url URL          Base URL to validate (default: http://localhost:18080)
  --output-dir DIR        Root directory for artifacts (default: artifacts/production-readiness)
  --json-only             Print report.json to stdout after generation
  --strict                Exit non-zero unless final score is READY
  --skip-heavy            Skip mutation-heavy or slower runtime validations
  -h, --help              Show this help
EOF
}

BASE_URL=""
OUTPUT_DIR="artifacts/production-readiness"
JSON_ONLY=false
STRICT=false
SKIP_HEAVY=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --json-only)
      JSON_ONLY=true
      shift
      ;;
    --strict)
      STRICT=true
      shift
      ;;
    --skip-heavy)
      SKIP_HEAVY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${BASE_URL}" ]]; then
  BASE_URL="$(default_base_url)"
fi

TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
OUTPUT_ROOT="${OUTPUT_DIR%/}"
RUN_DIR="${OUTPUT_ROOT}/${TIMESTAMP}"
LOGS_DIR="${RUN_DIR}/logs"
REPORT_MD="${RUN_DIR}/report.md"
REPORT_JSON="${RUN_DIR}/report.json"
mkdir -p "${LOGS_DIR}"

export PR_BASE_URL="${BASE_URL}"
export PR_RUN_DIR="${RUN_DIR}"
export PR_LOGS_DIR="${LOGS_DIR}"
export PR_REPORT_MD="${REPORT_MD}"
export PR_REPORT_JSON="${REPORT_JSON}"
export PR_SKIP_HEAVY="${SKIP_HEAVY}"

python3 <<'PY'
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.getcwd())
sys.path.insert(0, str(ROOT / "control_plane"))

from app.services.tts_readiness import (  # noqa: E402
    assess_tts_probe,
    build_tts_probe_skip,
    get_or_create_tts_readiness_client as ensure_tts_readiness_client,
)

BASE_URL = os.environ["PR_BASE_URL"].rstrip("/")
RUN_DIR = Path(os.environ["PR_RUN_DIR"])
LOGS_DIR = Path(os.environ["PR_LOGS_DIR"])
REPORT_MD = Path(os.environ["PR_REPORT_MD"])
REPORT_JSON = Path(os.environ["PR_REPORT_JSON"])
SKIP_HEAVY = os.environ.get("PR_SKIP_HEAVY", "false").lower() == "true"

ALLOWED_SCORES = {"READY", "READY_WITH_WARNINGS", "NOT_READY"}
OPTIONAL_SKIP_IDS = {
    "services_pocket_tts",
    "services_rag_worker",
    "api_streaming_sse",
    "tts_enabled_detected",
    "tts_generate_wav",
    "rag_multiclient_validation",
    "rag_safe_cleanup",
    "dr_last_report_detected",
    "dr_restore_dry_run",
    "observability_validate_script",
    "observability_validation_artifacts",
}

OPTIONAL_WARN_IDS = {
    "saas_rate_limit",
    "security_cors_local",
    "git_status_clean",
    "services_pocket_tts",
    "services_rag_worker",
}

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{10,}"),
    re.compile(r"(X-Admin-Token:\s*)([^\s]+)", re.IGNORECASE),
    re.compile(r"(Authorization:\s*Bearer\s+)([^\s]+)", re.IGNORECASE),
    re.compile(r"(ADMIN_TOKEN=)([^\s]+)"),
    re.compile(r"(JWT_SECRET=)([^\s]+)"),
]


def sanitize_text(value: str) -> str:
    if not value:
        return ""
    text = value
    for pattern in SECRET_PATTERNS:
        if pattern.groups >= 2:
            text = pattern.sub(r"\1[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED]", text)
    return text


def write_log(check_id: str, content: str) -> str:
    path = LOGS_DIR / f"{check_id}.log"
    path.write_text(sanitize_text(content), encoding="utf-8")
    return str(path.relative_to(RUN_DIR))


def bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on", "manual"}


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_version() -> str:
    version_file = ROOT / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip() or "unknown"
    return "unknown"


def run_cmd(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(args=args, returncode=127, stdout="", stderr=str(exc))


def run_shell(command: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["bash", "-lc", command],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(args=["bash", "-lc", command], returncode=127, stdout="", stderr=str(exc))


def http_request(
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: int = 15,
) -> tuple[int | None, str, dict[str, str], str | None]:
    url = path if path.startswith("http://") or path.startswith("https://") else f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method=method, data=body)
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = response.read().decode("utf-8", errors="replace")
            return response.status, payload, dict(response.headers.items()), None
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        return exc.code, payload, dict(exc.headers.items()), None
    except Exception as exc:  # noqa: BLE001
        return None, "", {}, str(exc)


def http_request_bytes(
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: int = 15,
) -> tuple[int | None, bytes, dict[str, str], str | None]:
    url = path if path.startswith("http://") or path.startswith("https://") else f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method=method, data=body)
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = response.read()
            return response.status, payload, dict(response.headers.items()), None
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        return exc.code, payload, dict(exc.headers.items()), None
    except Exception as exc:  # noqa: BLE001
        return None, b"", {}, str(exc)


def json_body(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


@dataclass
class CheckRecord:
    id: str
    category: str
    title: str
    status: str
    severity: str
    details: str
    remediation: str
    evidence: str
    readiness_impact: str = "none"
    optional: bool = False


checks: list[CheckRecord] = []


def add_check(
    check_id: str,
    category: str,
    title: str,
    status: str,
    severity: str,
    details: str,
    remediation: str,
    evidence: str,
    readiness_impact: str = "none",
    optional: bool = False,
) -> None:
    checks.append(
        CheckRecord(
            id=check_id,
            category=category,
            title=title,
            status=status,
            severity=severity,
            details=sanitize_text(details),
            remediation=sanitize_text(remediation),
            evidence=sanitize_text(evidence),
            readiness_impact=readiness_impact,
            optional=optional,
        )
    )


version = read_version()
git_branch = run_cmd(["git", "branch", "--show-current"]).stdout.strip() or "unknown"
git_commit = run_cmd(["git", "rev-parse", "HEAD"]).stdout.strip() or "unknown"
git_status = run_cmd(["git", "status", "--porcelain"])
git_status_clean = git_status.returncode == 0 and not git_status.stdout.strip()
generated_at = iso_now()
localhost_mode = bool_env("LOCALHOST_MODE", False)
appliance_mode = bool_env("LOCAL_APPLIANCE_MODE", False)
deployment_mode = os.environ.get("DEPLOYMENT_MODE", "appliance")
local_billing_mode = os.environ.get("LOCAL_BILLING_MODE", "")
# ... (around line 240)
add_check(
    "env_deployment_mode",
    "environment",
    "Deployment Mode",
    "pass",
    "low",
    f"mode={deployment_mode}",
    "Ajuste DEPLOYMENT_MODE conforme necessário (appliance|saas).",
    write_log("env_deployment_mode", f"DEPLOYMENT_MODE={deployment_mode}\n"),
)

if deployment_mode == "saas":
    # 1. Strong ADMIN_TOKEN for SaaS
    token_ok = len(admin_token) >= 32 and any(c.islower() for c in admin_token) and any(c.isupper() for c in admin_token) and any(c.isdigit() for c in admin_token)
    add_check(
        "saas_admin_token_strength",
        "security",
        "ADMIN_TOKEN força SaaS",
        "pass" if token_ok else "fail",
        "critical",
        "token atende requisitos SaaS (32+ chars, mixed case/digit)" if token_ok else "token não atende requisitos SaaS",
        "Aumente ADMIN_TOKEN para 32+ caracteres com letras maiúsculas, minúsculas e números.",
        write_log("saas_admin_token_strength", "check complete\n"),
    )
    
    # 2. Explicit CORS for SaaS
    # (reuse existing security_cors_local logic but force failure if it was warn/skip)
    
    # 3. Cost Guardrails defined
    max_global_cost = os.environ.get("MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL")
    add_check(
        "saas_cost_guardrails",
        "saas",
        "Guardrails financeiros SaaS",
        "pass" if max_global_cost else "warn",
        "high",
        f"MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL={max_global_cost}",
        "Configure limites financeiros globais para evitar gastos inesperados.",
        write_log("saas_cost_guardrails", f"global_limit={max_global_cost}\n"),
    )
rag_enabled = bool_env("RAG_ENABLED", True)
tts_enabled = bool_env("TTS_ENABLED", True)
app_public_url = os.environ.get("APP_PUBLIC_URL", BASE_URL)
admin_token = os.environ.get("ADMIN_TOKEN", "")

created_client_id: str | None = None
created_client_name: str | None = None
working_api_key: str | None = None
working_api_key_prefix: str | None = None
public_signup_client_id: str | None = None
temp_client_created = False


def cleanup_created_client() -> None:
    if temp_client_created and created_client_id and admin_token:
        http_request(
            f"/admin/clients/{created_client_id}",
            method="DELETE",
            headers={"X-Admin-Token": admin_token},
        )


def get_or_create_tts_readiness_client() -> tuple[bool, str]:
    global created_client_id, created_client_name, working_api_key, working_api_key_prefix, temp_client_created
    client = ensure_tts_readiness_client(http_request, admin_token)
    if not client.ok:
        return False, client.detail
    created_client_id = client.client_id
    created_client_name = client.client_name
    working_api_key = client.api_key
    working_api_key_prefix = client.key_prefix
    temp_client_created = client.temporary
    return True, client.detail


def provision_api_access() -> tuple[bool, str]:
    global created_client_id, created_client_name, working_api_key, working_api_key_prefix, public_signup_client_id, temp_client_created

    if working_api_key:
        return True, "api key already provisioned"

    if admin_token:
        status, body, _, error = http_request(
            "/admin/clients",
            headers={"X-Admin-Token": admin_token},
        )
        if status == 200:
            try:
                clients = json.loads(body)
            except json.JSONDecodeError:
                clients = []
            demo_client = next((item for item in clients if item.get("name") == "demo-client"), None)
            if demo_client:
                created_client_id = demo_client.get("id")
                created_client_name = demo_client.get("name")
            else:
                name = f"production-readiness-{int(time.time())}"
                payload = {
                    "name": name,
                    "description": "temporary client for production readiness",
                    "rate_limit_per_minute": 10,
                    "daily_token_quota": 100000,
                    "weekly_token_quota": 500000,
                    "monthly_token_quota": 2000000,
                    "max_output_tokens": 512,
                }
                create_status, create_body, _, create_error = http_request(
                    "/admin/clients",
                    method="POST",
                    headers={
                        "X-Admin-Token": admin_token,
                        "Content-Type": "application/json",
                    },
                    body=json_body(payload),
                )
                if create_status == 201:
                    try:
                        created = json.loads(create_body)
                    except json.JSONDecodeError:
                        created = {}
                    created_client_id = created.get("id")
                    created_client_name = created.get("name", name)
                    temp_client_created = True
                else:
                    return False, f"admin client creation failed: status={create_status} error={create_error or create_body[:160]}"

            if created_client_id:
                key_status, key_body, _, key_error = http_request(
                    "/admin/api-keys",
                    method="POST",
                    headers={
                        "X-Admin-Token": admin_token,
                        "Content-Type": "application/json",
                    },
                    body=json_body({"client_id": created_client_id, "name": "production-readiness"}),
                )
                if key_status == 201:
                    try:
                        created_key = json.loads(key_body)
                    except json.JSONDecodeError:
                        created_key = {}
                    working_api_key = created_key.get("api_key")
                    working_api_key_prefix = created_key.get("key_prefix")
                    if working_api_key:
                        return True, f"api key issued for client={created_client_name or created_client_id} prefix={working_api_key_prefix or 'masked'}"
                return False, f"admin api key creation failed: status={key_status} error={key_error or key_body[:160]}"

        if error:
            return False, f"admin access failed: {error}"

    signup_payload = {
        "full_name": "Production Readiness",
        "email": f"production-readiness-{int(time.time())}@example.com",
        "company": "Localhost",
        "plan_code": "free",
        "use_case": "local-production readiness validation",
    }
    status, body, _, error = http_request(
        "/public/signup",
        method="POST",
        headers={"Content-Type": "application/json"},
        body=json_body(signup_payload),
    )
    if status == 201:
        try:
            created = json.loads(body)
        except json.JSONDecodeError:
            created = {}
        public_signup_client_id = created.get("client_id")
        working_api_key = created.get("api_key")
        working_api_key_prefix = created.get("api_key_prefix")
        if working_api_key:
            return True, f"api key issued via public signup client={public_signup_client_id} prefix={working_api_key_prefix or 'masked'}"
    return False, f"public signup failed: status={status} error={error or body[:160]}"


def auth_headers() -> dict[str, str]:
    if not working_api_key:
        return {}
    return {"Authorization": f"Bearer {working_api_key}"}


def add_command_check(
    check_id: str,
    category: str,
    title: str,
    severity: str,
    args: list[str],
    pass_condition,
    remediation: str,
    timeout: int = 20,
) -> None:
    result = run_cmd(args, timeout=timeout)
    combined = f"$ {' '.join(shlex.quote(part) for part in args)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    evidence = write_log(check_id, combined)
    status = "pass" if pass_condition(result) else "fail"
    details = (
        f"command succeeded with exit code {result.returncode}"
        if status == "pass"
        else f"command failed with exit code {result.returncode}"
    )
    add_check(check_id, category, title, status, severity, details, remediation, evidence)


add_check(
    "git_branch",
    "git_release",
    "Branch atual detectada",
    "pass" if git_branch != "unknown" else "fail",
    "low",
    f"branch atual: {git_branch}",
    "Execute o relatório dentro de um checkout Git válido.",
    write_log("git_branch", git_branch + "\n"),
)
add_check(
    "git_commit",
    "git_release",
    "Commit atual detectado",
    "pass" if git_commit != "unknown" else "fail",
    "low",
    f"commit atual: {git_commit}",
    "Garanta que o repositório tenha histórico Git acessível.",
    write_log("git_commit", git_commit + "\n"),
)
add_check(
    "git_status_clean",
    "git_release",
    "Working tree clean/dirty",
    "pass" if git_status_clean else "warn",
    "medium",
    "working tree limpo" if git_status_clean else "working tree possui alterações locais",
    "Revise e committed/stashe alterações não relacionadas antes da liberação local-production.",
    write_log("git_status_clean", git_status.stdout or "(clean)\n"),
)
tags_result = run_cmd(["git", "tag", "-l", "*local-production*"])
tags = [line.strip() for line in tags_result.stdout.splitlines() if line.strip()]
add_check(
    "git_local_production_tag",
    "git_release",
    "Tag local-production existente",
    "pass" if tags else "fail",
    "high",
    "tags local-production encontradas" if tags else "nenhuma tag local-production encontrada",
    "Crie ou sincronize a tag base local-production antes da operação.",
    write_log("git_local_production_tag", "\n".join(tags) + ("\n" if tags else "")),
)
version_file = ROOT / "VERSION"
add_check(
    "git_version_file",
    "git_release",
    "Arquivo VERSION existe",
    "pass" if version_file.exists() and version else "fail",
    "high",
    f"VERSION={version}" if version_file.exists() else "arquivo VERSION ausente",
    "Adicione e mantenha o arquivo VERSION alinhado com a release local-production.",
    write_log("git_version_file", f"{version}\n" if version_file.exists() else ""),
)

for tool_name in ("docker", "curl", "jq"):
    add_command_check(
        f"env_{tool_name}",
        "environment",
        f"{tool_name} disponível",
        "critical" if tool_name == "curl" else "high",
        ["bash", "-lc", f"command -v {tool_name}"],
        lambda result: result.returncode == 0 and bool(result.stdout.strip()),
        f"Instale {tool_name} no host antes de operar em local-production.",
    )

compose_probe = run_cmd(["docker", "compose", "version"])
compose_log = write_log("env_docker_compose", f"stdout:\n{compose_probe.stdout}\nstderr:\n{compose_probe.stderr}")
add_check(
    "env_docker_compose",
    "environment",
    "docker compose disponível",
    "pass" if compose_probe.returncode == 0 else "fail",
    "critical",
    "docker compose disponível" if compose_probe.returncode == 0 else "docker compose indisponível",
    "Instale Docker Compose v2 e valide `docker compose version`.",
    compose_log,
)
add_check(
    "env_base_url",
    "environment",
    "Base URL configurada",
    "pass" if BASE_URL.startswith("http://") or BASE_URL.startswith("https://") else "fail",
    "critical",
    f"base_url={BASE_URL}",
    "Informe `--base-url http://localhost:18080` ou ajuste a configuração local.",
    write_log("env_base_url", BASE_URL + "\n"),
)
add_check(
    "env_localhost_mode",
    "environment",
    "LOCALHOST_MODE habilitado",
    "pass" if localhost_mode else "warn",
    "high",
    f"LOCALHOST_MODE={localhost_mode}",
    "Ative LOCALHOST_MODE=true no ambiente local-production para manter compatibilidade com localhost.",
    write_log("env_localhost_mode", f"LOCALHOST_MODE={localhost_mode}\nAPP_PUBLIC_URL={app_public_url}\n"),
)

compose_ps = run_cmd(["docker", "compose", "--env-file", os.environ.get("STACK_ENV_FILE", ".env.example"), "-f", "docker-compose.yml", "ps"], timeout=30)
compose_ps_log = write_log("services_docker_compose_ps", f"stdout:\n{compose_ps.stdout}\nstderr:\n{compose_ps.stderr}")
add_check(
    "services_docker_compose_ps",
    "services",
    "docker compose ps",
    "pass" if compose_ps.returncode == 0 else "fail",
    "critical",
    "docker compose ps executado" if compose_ps.returncode == 0 else "falha ao executar docker compose ps",
    "Suba a stack com `./scripts/dev/local-production-up.sh` e valide o Docker Compose.",
    compose_ps_log,
)

services_output = compose_ps.stdout.lower()
for service_name, severity, optional in (
    ("postgres", "critical", False),
    ("redis", "critical", False),
    ("control-plane", "critical", False),
    ("data-plane-gemma", "critical", False),
    ("pocket-tts", "medium", True),
    ("rag-worker", "medium", True),
):
    check_id = f"services_{service_name.replace('-', '_')}"
    if compose_ps.returncode != 0:
        add_check(
            check_id,
            "services",
            f"Serviço {service_name}",
            "fail" if not optional else "skip",
            severity,
            "docker compose ps indisponível",
            "Revalide o Docker Compose e suba o serviço correspondente.",
            compose_ps_log,
        )
        continue
    if service_name in services_output:
        is_up = any(token in services_output for token in (f"{service_name.lower()}") ) and not re.search(
            rf"{re.escape(service_name.lower())}.*\b(exit|created|restarting|dead)\b",
            services_output,
        )
        add_check(
            check_id,
            "services",
            f"Serviço {service_name}",
            "pass" if is_up else "fail",
            severity,
            f"{service_name} detectado em docker compose ps" if is_up else f"{service_name} detectado, mas sem estado saudável aparente",
            f"Suba ou recupere o serviço `{service_name}`.",
            compose_ps_log,
        )
    else:
        add_check(
            check_id,
            "services",
            f"Serviço {service_name}",
            "skip" if optional else "fail",
            severity,
            f"{service_name} não encontrado na saída do compose",
            f"Se `{service_name}` fizer parte do perfil esperado, habilite-o e reexecute o relatório.",
            compose_ps_log,
        )

health_status, health_body, _, health_error = http_request("/health")
health_log = write_log("api_health", f"status={health_status}\nerror={health_error}\nbody:\n{health_body}")
add_check(
    "api_health",
    "api",
    "GET /health",
    "pass" if health_status == 200 and '"status"' in health_body else "fail",
    "critical",
    f"HTTP {health_status}" if health_status is not None else f"erro de conexão: {health_error}",
    "Suba o control-plane e exponha a API em localhost antes da operação local-production.",
    health_log,
)
ready_status, ready_body, _, ready_error = http_request("/ready")
ready_log = write_log("api_ready", f"status={ready_status}\nerror={ready_error}\nbody:\n{ready_body}")
add_check(
    "api_ready",
    "api",
    "GET /ready",
    "pass" if ready_status == 200 and '"ready"' in ready_body else "fail",
    "critical",
    f"HTTP {ready_status}" if ready_status is not None else f"erro de conexão: {ready_error}",
    "Corrija dependências de readiness, migrations e conectividade de banco/redis.",
    ready_log,
)
status_status, status_body, _, status_error = http_request("/status")
status_log = write_log("api_status", f"status={status_status}\nerror={status_error}\nbody:\n{status_body}")
api_status_ok = status_status == 200 and '"status"' in status_body
add_check(
    "api_status",
    "api",
    "GET /status",
    "pass" if api_status_ok else "fail",
    "critical",
    f"HTTP {status_status}" if status_status is not None else f"erro de conexão: {status_error}",
    "Recupere banco, redis e inference plane até /status responder com sucesso.",
    status_log,
)

api_access_ok, api_access_details = provision_api_access()
api_access_log = write_log("saas_api_key_bootstrap", api_access_details + "\n")

models_status, models_body, _, models_error = http_request("/v1/models", headers=auth_headers())
models_log = write_log("api_v1_models", f"status={models_status}\nerror={models_error}\nbody:\n{models_body}")
models_list = []
if models_status == 200:
    try:
        models_list = json.loads(models_body).get("data", [])
    except Exception:  # noqa: BLE001
        models_list = []
add_check(
    "api_v1_models",
    "api",
    "GET /v1/models",
    "pass" if models_status == 200 and isinstance(models_list, list) else "fail",
    "critical",
    f"HTTP {models_status}; modelos retornados={len(models_list)}" if models_status is not None else f"erro de conexão: {models_error}",
    "Garanta autenticação funcional e registro de modelos ativos no control-plane.",
    models_log,
)

selected_model = ""
if models_list:
    selected_model = models_list[0].get("id") or models_list[0].get("model_id") or ""

chat_capable_model = ""
ready_chat_model = ""
for model in models_list:
    model_id = model.get("id") or model.get("model_id") or ""
    capabilities = model.get("capabilities") or {}
    
    # Nova lógica baseada em capabilities explícitas
    if capabilities.get("chat") is True:
        if not chat_capable_model:
            chat_capable_model = model_id
        
        # Priorizar modelo que já está pronto (backend online ou mock habilitado)
        if model.get("local_ready") is True or model.get("production_ready") is True:
            ready_chat_model = model_id
            break

chat_probe_model = ready_chat_model or chat_capable_model or selected_model or "default"
chat_streaming_supported = False
if chat_probe_model != "default":
    target_model = next((m for m in models_list if (m.get("id") or m.get("model_id")) == chat_probe_model), None)
    if target_model:
        chat_streaming_supported = target_model.get("capabilities", {}).get("streaming") is True

chat_payload = {
    "model": chat_probe_model,
    "messages": [{"role": "user", "content": "Return only the word ok."}],
    "max_tokens": 10,
    "temperature": 0,
    "stream": False,
}
chat_status, chat_body, _, chat_error = http_request(
    "/v1/chat/completions",
    method="POST",
    headers={**auth_headers(), "Content-Type": "application/json"},
    body=json_body(chat_payload),
    timeout=60,
)
chat_log = write_log("api_chat_completions", f"status={chat_status}\nerror={chat_error}\nbody:\n{chat_body}")
chat_ok = chat_status == 200 and ("choices" in chat_body or '"id"' in chat_body)
chat_status_label = "pass" if chat_ok else "fail"
chat_details = f"HTTP {chat_status}" if chat_status is not None else f"erro de conexão: {chat_error}"
chat_remediation = "Recupere autenticação de cliente, modelos registrados e data plane antes da operação."

if chat_ok:
    if "ok" in chat_body.lower():
        chat_details += "; Resposta 'ok' validada."
    else:
        chat_status_label = "warn"
        chat_details += "; Resposta recebida mas não contém 'ok'."
else:
    if ready_chat_model:
         chat_status_label = "fail"
         chat_details = f"HTTP {chat_status}; Modelo {ready_chat_model} marcado como pronto mas falhou no teste real."
    elif chat_capable_model:
         chat_status_label = "warn"
         chat_details = f"HTTP {chat_status}; /v1/models encontrou modelo de chat {chat_capable_model} mas ele não está local_ready."
         chat_remediation = "Verifique o status do backend para o modelo ou habilite MOCK_BACKEND_ENABLED para testes locais."
    else:
         chat_status_label = "warn"
         chat_details = f"HTTP {chat_status}; /v1/models não expôs modelo de chat utilizável (probe={chat_probe_model})"
         chat_remediation = "Publique ao menos um modelo generativo em /v1/models para validar chat ponta a ponta neste relatório."

add_check(
    "api_chat_completions",
    "api",
    "POST /v1/chat/completions",
    chat_status_label,
    "critical",
    chat_details,
    chat_remediation,
    chat_log,
)

stream_payload = dict(chat_payload)
stream_payload["stream"] = True
stream_status, stream_body, stream_headers, stream_error = http_request(
    "/v1/chat/completions",
    method="POST",
    headers={**auth_headers(), "Content-Type": "application/json"},
    body=json_body(stream_payload),
    timeout=60,
)
stream_log = write_log(
    "api_streaming_sse",
    f"status={stream_status}\nerror={stream_error}\nheaders={json.dumps(stream_headers, indent=2)}\nbody:\n{stream_body[:4000]}",
)

has_sse_data = "data:" in stream_body
is_sse_content_type = "text/event-stream" in stream_headers.get("Content-Type", "")
stream_ok = stream_status == 200 and (has_sse_data or is_sse_content_type)

if stream_ok:
    stream_status_label = "pass"
    stream_details = f"HTTP {stream_status}; Stream SSE validado (chunks detectados)."
elif not chat_streaming_supported:
    stream_status_label = "skip"
    stream_details = f"Streaming ignorado: modelo {chat_probe_model} não reporta capability 'streaming'."
else:
    stream_status_label = "fail"
    stream_details = f"HTTP {stream_status}; Streaming falhou para modelo {chat_probe_model} que deveria suportar SSE."

add_check(
    "api_streaming_sse",
    "api",
    "Streaming SSE suportado",
    stream_status_label,
    "medium",
    stream_details,
    "Se streaming for requisito do caso local, valide o backend/modelo com suporte SSE.",
    stream_log,
)

metrics_status, metrics_body, _, metrics_error = http_request("/metrics", timeout=20)
metrics_log = write_log("api_metrics", f"status={metrics_status}\nerror={metrics_error}\nbody:\n{metrics_body[:4000]}")
add_check(
    "api_metrics",
    "api",
    "GET /metrics",
    "pass" if metrics_status == 200 and "requests_total" in metrics_body else "fail",
    "high",
    f"HTTP {metrics_status}" if metrics_status is not None else f"erro de conexão: {metrics_error}",
    "Exponha métricas Prometheus no control-plane antes de operar.",
    metrics_log,
)

plans_status, plans_body, _, plans_error = http_request(
    "/admin/billing/plans",
    headers={"X-Admin-Token": admin_token} if admin_token else {},
)
plans_log = write_log("saas_plans_exist", f"status={plans_status}\nerror={plans_error}\nbody:\n{plans_body}")
plans_ok = False
if plans_status == 200:
    try:
        plans_ok = len(json.loads(plans_body)) > 0
    except Exception:  # noqa: BLE001
        plans_ok = False
add_check(
    "saas_plans_exist",
    "saas",
    "Planos existem",
    "pass" if plans_ok else "fail",
    "high",
    f"HTTP {plans_status}; planos_detectados={plans_ok}" if plans_status is not None else f"erro de conexão: {plans_error}",
    "Carregue os billing plans padrão e valide o acesso admin.",
    plans_log,
)
add_check(
    "saas_demo_client",
    "saas",
    "Cliente demo/teste existe ou pode ser criado",
    "pass" if api_access_ok else "fail",
    "high",
    api_access_details,
    "Garanta ADMIN_TOKEN funcional ou `/public/signup` habilitado para provisionar um cliente local.",
    api_access_log,
)

api_key_status, api_key_body, _, api_key_error = http_request("/portal/me", headers=auth_headers())
api_key_log = write_log("saas_api_key_works", f"status={api_key_status}\nerror={api_key_error}\nbody:\n{api_key_body}")
add_check(
    "saas_api_key_works",
    "saas",
    "API key funciona",
    "pass" if api_key_status == 200 and '"billing_status"' in api_key_body else "fail",
    "critical",
    f"HTTP {api_key_status}" if api_key_status is not None else f"erro de conexão: {api_key_error}",
    "Reemita a API key e valide autenticação de cliente no portal/API.",
    api_key_log,
)

quota_status, quota_body, _, quota_error = http_request("/portal/usage", headers=auth_headers())
quota_log = write_log("saas_quotas", f"status={quota_status}\nerror={quota_error}\nbody:\n{quota_body}")
quota_ok = quota_status == 200 and '"daily_usage"' in quota_body and '"monthly_usage"' in quota_body
add_check(
    "saas_quotas",
    "saas",
    "Quotas expostas",
    "pass" if quota_ok else "fail",
    "high",
    f"HTTP {quota_status}" if quota_status is not None else f"erro de conexão: {quota_error}",
    "Garanta cálculo de quota ativo e endpoints do portal acessíveis ao cliente.",
    quota_log,
)

rate_limit_status = "skip" if SKIP_HEAVY else "warn"
rate_limit_details = "checagem pesada omitida" if SKIP_HEAVY else "não executada"
rate_limit_evidence = write_log("saas_rate_limit", rate_limit_details + "\n")
if not SKIP_HEAVY:
    script_path = ROOT / "scripts" / "validate-rate-limit-readiness-local.sh"
    if script_path.exists():
        # Pass BASE_URL and ADMIN_TOKEN to the script
        env = os.environ.copy()
        env["BASE_URL"] = BASE_URL
        env["ADMIN_TOKEN"] = admin_token
        try:
            result = subprocess.run(
                [str(script_path)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
                env=env
            )
            rate_limit_evidence = write_log("saas_rate_limit", f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
            rate_limit_status = "pass" if result.returncode == 0 else "fail"
            m = re.search(r"evidence=(.*)", result.stdout)
            rate_limit_details = m.group(1) if m else f"validate-rate-limit-readiness-local.sh exit_code={result.returncode}"
        except Exception as e:
            rate_limit_status = "fail"
            rate_limit_details = f"erro ao executar probe: {str(e)}"
            rate_limit_evidence = write_log("saas_rate_limit", rate_limit_details)
    else:
        rate_limit_details = "script de validação não encontrado"
add_check(
    "saas_rate_limit",
    "saas",
    "Rate limit básico",
    rate_limit_status,
    "high",
    rate_limit_details,
    "Valide rate limit com cliente de teste e ajuste Redis/limites por plano.",
    rate_limit_evidence,
)

portal_invoices_status, portal_invoices_body, _, portal_invoices_error = http_request("/portal/invoices", headers=auth_headers())
billing_log = write_log("saas_billing_local_manual", f"status={portal_invoices_status}\nerror={portal_invoices_error}\nbody:\n{portal_invoices_body}")
billing_ok = portal_invoices_status == 200 and "manual/local" in portal_invoices_body
add_check(
    "saas_billing_local_manual",
    "saas",
    "Billing local/manual",
    "pass" if billing_ok else "fail",
    "high",
    f"HTTP {portal_invoices_status}; local/manual detectado={billing_ok}" if portal_invoices_status is not None else f"erro de conexão: {portal_invoices_error}",
    "Mantenha LOCAL_BILLING_MODE=manual e valide o portal de invoices.",
    billing_log,
)

suspend_status = "skip" if SKIP_HEAVY else "warn"
suspend_details = "checagem pesada omitida" if SKIP_HEAVY else "não executada"
suspend_evidence = write_log("saas_suspend_unsuspend", suspend_details + "\n")
if not SKIP_HEAVY:
    script_path = ROOT / "scripts" / "validate-local-billing.sh"
    if script_path.exists():
        result = run_cmd([str(script_path)], timeout=180)
        suspend_evidence = write_log("saas_suspend_unsuspend", f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        suspend_status = "pass" if result.returncode == 0 else "fail"
        suspend_details = f"validate-local-billing.sh exit_code={result.returncode}"
add_check(
    "saas_suspend_unsuspend",
    "saas",
    "Suspensão/desbloqueio",
    suspend_status,
    "high",
    suspend_details,
    "Valide o fluxo de overdue, suspensão e pagamento manual local.",
    suspend_evidence,
)

add_check(
    "rag_enabled_detected",
    "rag",
    "RAG habilitado/desabilitado detectado",
    "pass",
    "medium",
    f"RAG_ENABLED={rag_enabled}",
    "Ajuste RAG_ENABLED conforme a operação local desejada.",
    write_log("rag_enabled_detected", f"RAG_ENABLED={rag_enabled}\n"),
)
rag_validation_script = ROOT / "scripts" / "validate-rag-local-multiclient.sh"
if rag_validation_script.exists():
    if SKIP_HEAVY:
        add_check(
            "rag_multiclient_validation",
            "rag",
            "Isolamento multi-cliente via validate-rag-local-multiclient.sh",
            "skip",
            "medium",
            "checagem pesada omitida por --skip-heavy",
            "Execute o script dedicado para validar isolamento RAG entre clientes.",
            write_log("rag_multiclient_validation", "skipped due to --skip-heavy\n"),
        )
    else:
        result = run_cmd([str(rag_validation_script)], timeout=240)
        evidence = write_log("rag_multiclient_validation", f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        add_check(
            "rag_multiclient_validation",
            "rag",
            "Isolamento multi-cliente via validate-rag-local-multiclient.sh",
            "pass" if result.returncode == 0 else "fail",
            "high",
            f"script exit_code={result.returncode}",
            "Corrija isolamento por cliente antes de operar RAG em modo local-production.",
            evidence,
        )
else:
    add_check(
        "rag_multiclient_validation",
        "rag",
        "Isolamento multi-cliente via validate-rag-local-multiclient.sh",
        "skip",
        "medium",
        "script não existe",
        "Adicione validação automática de isolamento RAG.",
        write_log("rag_multiclient_validation", "script missing\n"),
    )

clean_rag_script = ROOT / "scripts" / "clean-rag-local-data.sh"
if clean_rag_script.exists():
    result = run_cmd([str(clean_rag_script), "--dry-run"], timeout=120)
    evidence = write_log("rag_safe_cleanup", f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    add_check(
        "rag_safe_cleanup",
        "rag",
        "Limpeza segura via clean-rag-local-data.sh",
        "pass" if result.returncode == 0 else "fail",
        "medium",
        f"script exit_code={result.returncode}",
        "Corrija o script de limpeza segura para preservar modelos e código.",
        evidence,
    )
else:
    add_check(
        "rag_safe_cleanup",
        "rag",
        "Limpeza segura via clean-rag-local-data.sh",
        "skip",
        "medium",
        "script não existe",
        "Adicione um fluxo de limpeza segura para dados RAG locais.",
        write_log("rag_safe_cleanup", "script missing\n"),
    )

pocket_tts_script = ROOT / "scripts" / "pocket-tts.sh"
tts_present = pocket_tts_script.exists()
add_check(
    "tts_enabled_detected",
    "tts",
    "TTS habilitado/desabilitado detectado",
    "pass" if tts_enabled else "skip",
    "medium",
    f"TTS_ENABLED={tts_enabled}" + (" (scripts/dev/pocket-tts.sh detectado)" if tts_present else " (scripts/dev/pocket-tts.sh ausente)"),
    "Ajuste TTS_ENABLED conforme a operação local desejada.",
    write_log("tts_enabled_detected", f"tts_enabled={tts_enabled}\npocket_tts_script={tts_present}\n"),
)
if tts_enabled and tts_present and not SKIP_HEAVY:
    tts_client_ok, tts_client_details = get_or_create_tts_readiness_client()
    status = None
    headers = {}
    error = None
    response_body = b""
    usage_recorded = False
    wav_path = RUN_DIR / "logs" / "tts-sample.wav"

    if tts_client_ok:
        status, response_body, headers, error = http_request_bytes(
            "/pocket-tts/tts",
            method="POST",
            body=urllib.parse.urlencode({"text": "readiness tts ok"}).encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                **auth_headers(),
            },
            timeout=60,
        )
        if status in {200, 201} and response_body:
            wav_path.write_bytes(response_body)

        if created_client_id and admin_token:
            usage_status, usage_body, _, _ = http_request(
                f"/admin/usage/{created_client_id}/summary",
                headers={"X-Admin-Token": admin_token},
            )
            if usage_status == 200:
                try:
                    usage_payload = json.loads(usage_body)
                except json.JSONDecodeError:
                    usage_payload = {}
                usage_recorded = int(usage_payload.get("today", {}).get("tts_chars_used", 0)) > 0
    assessment = assess_tts_probe(
        tts_enabled=tts_enabled,
        http_status=status,
        headers=headers,
        body=response_body,
        usage_recorded=usage_recorded,
        client_detail=tts_client_details,
    )
    evidence = write_log(
        "tts_generate_wav",
        (
            f"client_status={tts_client_details}\n"
            f"client_ready={tts_client_ok}\n"
            f"status={status}\n"
            f"error={error}\n"
            f"content_type={headers.get('Content-Type', '')}\n"
            f"usage_recorded={usage_recorded}\n"
            f"body_preview={response_body[:200].decode('utf-8', errors='replace')}\n"
        ),
    )
    add_check(
        "tts_generate_wav",
        "tts",
        "Geração local .wav",
        assessment.status,
        "medium",
        assessment.details if tts_client_ok else f"falha ao preparar client readiness: {tts_client_details}",
        assessment.remediation if tts_client_ok else "Configure ADMIN_TOKEN e um billing plan ativo com tts_enabled=true para o probe autenticado.",
        evidence,
        optional=assessment.optional,
    )
    if wav_path.exists():
        wav_path.unlink()
else:
    skip_assessment = build_tts_probe_skip(
        "checagem omitida por --skip-heavy" if SKIP_HEAVY and tts_enabled and tts_present else "TTS desabilitado ou scripts ausentes"
    )
    add_check(
        "tts_generate_wav",
        "tts",
        "Geração local .wav",
        skip_assessment.status,
        "medium",
        skip_assessment.details,
        skip_assessment.remediation,
        write_log("tts_generate_wav", "skipped\n"),
        optional=skip_assessment.optional,
    )

gitignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
audio_storage_ok = "artifacts/" in gitignore_text or "*.wav" in gitignore_text
add_check(
    "tts_audio_storage_out_of_git",
    "tts",
    "Storage de áudio fora do Git",
    "pass" if audio_storage_ok else "warn",
    "medium",
    "artefatos/wav ignorados pelo Git" if audio_storage_ok else "não há regra clara para ignorar áudio gerado",
    "Garanta que áudio gerado fique em artifacts/ ou outra área ignorada pelo Git.",
    write_log("tts_audio_storage_out_of_git", gitignore_text),
)

secrets_result = run_cmd([str(ROOT / "scripts" / "check-secrets.sh"), "--all"], timeout=180)
secrets_evidence = write_log("security_check_secrets", f"stdout:\n{secrets_result.stdout}\nstderr:\n{secrets_result.stderr}")
add_check(
    "security_check_secrets",
    "security",
    "check-secrets --all",
    "pass" if secrets_result.returncode == 0 else "fail",
    "critical",
    f"check-secrets exit_code={secrets_result.returncode}",
    "Remova secrets versionados antes de qualquer operação ou release local-production.",
    secrets_evidence,
)
for rel_path, title, pattern in (
    (".env", ".env não versionado", ".env"),
    (".local", ".local não versionado", ".local .local/*"),
):
    result = run_cmd(["bash", "-lc", f"git ls-files {pattern}"])
    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    add_check(
        f"security_{rel_path.replace('.', '').replace('/', '_')}_not_versioned",
        "security",
        title,
        "pass" if not tracked else "fail",
        "critical" if rel_path == ".env" else "high",
        f"{rel_path} não está versionado" if not tracked else f"{rel_path} está versionado",
        f"Remova {rel_path} do Git e mantenha apenas exemplos higienizados.",
        write_log(f"security_{rel_path.replace('.', '').replace('/', '_')}_not_versioned", f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"),
    )
for rel_path, title in (("backups", "backups/ não versionado"), ("exports", "exports/ não versionado")):
    result = run_cmd(["bash", "-lc", f"git ls-files '{rel_path}/*' '{rel_path}'"])
    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    add_check(
        f"security_{rel_path}_not_versioned",
        "security",
        title,
        "pass" if not tracked else "fail",
        "high",
        f"{rel_path} fora do Git" if not tracked else f"{rel_path} possui arquivos versionados",
        f"Remova `{rel_path}/` do Git e mantenha a pasta apenas para artefatos locais.",
        write_log(f"security_{rel_path}_not_versioned", f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"),
    )
add_check(
    "security_rag_uploads_gitignore",
    "security",
    "data/rag_uploads no .gitignore",
    "pass" if "data/rag_uploads/" in gitignore_text else "fail",
    "critical",
    "regra encontrada" if "data/rag_uploads/" in gitignore_text else "regra ausente",
    "Adicione `data/rag_uploads/` ao .gitignore.",
    write_log("security_rag_uploads_gitignore", gitignore_text),
)
tracked_gguf = run_cmd(["bash", "-lc", "git ls-files 'models/*' '*.gguf'"])
tracked_gguf_lines = [line for line in tracked_gguf.stdout.splitlines() if line.strip()]
add_check(
    "security_models_gguf_out_of_git",
    "security",
    "models/.gguf fora do Git",
    "pass" if not tracked_gguf_lines else "fail",
    "critical",
    "nenhum .gguf versionado" if not tracked_gguf_lines else f".gguf versionados detectados: {len(tracked_gguf_lines)}",
    "Remova modelos do Git e mantenha `models/`/`*.gguf` ignorados.",
    write_log("security_models_gguf_out_of_git", tracked_gguf.stdout),
)
admin_protected_status, admin_protected_body, _, admin_protected_error = http_request("/admin/status")
admin_protected_log = write_log("security_admin_protected", f"status={admin_protected_status}\nerror={admin_protected_error}\nbody:\n{admin_protected_body}")
admin_protected_ok = admin_protected_status in {401, 403}
add_check(
    "security_admin_protected",
    "security",
    "Endpoints admin protegidos",
    "pass" if admin_protected_ok else "fail",
    "critical",
    f"HTTP {admin_protected_status}" if admin_protected_status is not None else f"erro de conexão: {admin_protected_error}",
    "Exija token admin nos endpoints administrativos.",
    admin_protected_log,
)
cors_status, cors_body, cors_headers, cors_error = http_request(
    "/health",
    method="OPTIONS",
    headers={
        "Origin": "http://localhost:18080",
        "Access-Control-Request-Method": "GET",
    },
)
cors_log = write_log("security_cors_local", f"status={cors_status}\nerror={cors_error}\nheaders={json.dumps(cors_headers, indent=2)}\nbody:\n{cors_body}")
cors_value = next((v for k, v in cors_headers.items() if k.lower() == "access-control-allow-origin"), "")

# Valid if localhost is allowed AND it's not '*' in appliance mode (though '*' might be ok for dev)
# We also check if BASE_URL is allowed
base_origin = BASE_URL.rstrip("/")
cors_status, _, cors_headers_base, _ = http_request(
    "/health",
    method="OPTIONS",
    headers={
        "Origin": base_origin,
        "Access-Control-Request-Method": "GET",
    },
)
cors_value_base = next((v for k, v in cors_headers_base.items() if k.lower() == "access-control-allow-origin"), "")

cors_ok = (cors_status in {200, 204} and 
           (cors_value == "http://localhost:18080" or cors_value == base_origin or "localhost" in cors_value))

# In appliance or SaaS mode, '*' is explicitly a warning/fail
is_appliance = appliance_mode or os.environ.get("LOCAL_APPLIANCE_MODE", "").lower() == "true"
is_saas = deployment_mode == "saas"
if (is_appliance or is_saas) and cors_value == "*":
    cors_ok = False
    cors_details = f"CORS wildcard '*' detectado em modo {deployment_mode}. Use origens explícitas."
    cors_severity = "critical" if is_saas else "high"
elif cors_ok:
    cors_details = f"HTTP {cors_status}; allow-origin={cors_value}"
    cors_severity = "medium"
else:
    cors_details = f"CORS restritivo ou inválido: allow-origin={cors_value}"
    cors_severity = "high"

add_check(
    "security_cors_local",
    "security",
    "CORS local",
    "pass" if cors_ok else ("fail" if is_saas else "warn"),
    cors_severity,
    cors_details,
    "Configure CORS_ALLOW_ORIGINS com localhost e a URL base do appliance.",
    cors_log,
)
artifact_scan_seed = "\n".join(
    f"{item.name}" for item in LOGS_DIR.iterdir()
) + "\n"
add_check(
    "security_logs_without_full_keys",
    "security",
    "Logs/artifacts sem API keys completas",
    "pass",
    "critical",
    "o script sanitiza headers/tokens antes de persistir evidências",
    "Mantenha sanitização ativa e faça varredura final dos artefatos antes de publicar.",
    write_log("security_logs_without_full_keys", artifact_scan_seed),
)

backup_local = ROOT / "scripts" / "backup-local.sh"
restore_local = ROOT / "scripts" / "restore-local.sh"
dr_local = ROOT / "scripts" / "dr-test-local.sh"
add_check(
    "dr_backup_restore_scripts",
    "dr",
    "Scripts de backup/restore existem",
    "pass" if backup_local.exists() and restore_local.exists() else "fail",
    "high",
    f"backup-local={backup_local.exists()} restore-local={restore_local.exists()}",
    "Mantenha scripts dedicados de backup/restore no repositório.",
    write_log("dr_backup_restore_scripts", f"backup-local={backup_local.exists()}\nrestore-local={restore_local.exists()}\n"),
)
add_check(
    "dr_test_local_exists",
    "dr",
    "dr-test-local.sh existe",
    "pass" if dr_local.exists() else "fail",
    "high",
    f"dr-test-local.sh existe={dr_local.exists()}",
    "Adicione um teste DR local automatizado.",
    write_log("dr_test_local_exists", f"{dr_local}\n"),
)
dr_reports_root = ROOT / "artifacts" / "dr-tests"
dr_reports = sorted([item for item in dr_reports_root.glob("*/summary.json")], key=lambda p: p.stat().st_mtime) if dr_reports_root.exists() else []
add_check(
    "dr_last_report_detected",
    "dr",
    "Último relatório DR detectado",
    "pass" if dr_reports else "skip",
    "low",
    f"último relatório: {dr_reports[-1].as_posix()}" if dr_reports else "nenhum relatório DR encontrado",
    "Rode `./scripts/dev/dr-test-local.sh` para produzir evidência DR local.",
    write_log("dr_last_report_detected", "\n".join(str(item) for item in dr_reports) + ("\n" if dr_reports else "")),
)
restore_help = run_cmd([str(restore_local), "--help"], timeout=20) if restore_local.exists() else None
restore_dry_run_supported = restore_help is not None and "--dry-run" in (restore_help.stdout + restore_help.stderr)
add_check(
    "dr_restore_dry_run",
    "dr",
    "Restore dry-run, se suportado",
    "pass" if restore_dry_run_supported else "skip",
    "medium",
    "restore-local.sh expõe --dry-run" if restore_dry_run_supported else "restore-local.sh sem evidência de --dry-run",
    "Adicione ou preserve `--dry-run` no restore local.",
    write_log("dr_restore_dry_run", (restore_help.stdout + restore_help.stderr) if restore_help else "restore script missing\n"),
)

add_check(
    "observability_metrics_available",
    "observability",
    "/metrics disponível",
    "pass" if metrics_status == 200 else "fail",
    "high",
    f"HTTP {metrics_status}" if metrics_status is not None else f"erro de conexão: {metrics_error}",
    "Exponha métricas Prometheus no control-plane.",
    metrics_log,
)
observability_script = ROOT / "scripts" / "validate-observability-local.sh"
if observability_script.exists():
    if SKIP_HEAVY:
        add_check(
            "observability_validate_script",
            "observability",
            "validate-observability-local.sh",
            "skip",
            "medium",
            "checagem pesada omitida por --skip-heavy",
            "Execute a validação dedicada de observabilidade.",
            write_log("observability_validate_script", "skipped due to --skip-heavy\n"),
        )
    else:
        result = run_cmd([str(observability_script)], timeout=240)
        add_check(
            "observability_validate_script",
            "observability",
            "validate-observability-local.sh",
            "pass" if result.returncode == 0 else "fail",
            "high",
            f"script exit_code={result.returncode}",
            "Corrija a cadeia de métricas e artefatos de observabilidade.",
            write_log("observability_validate_script", f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"),
        )
else:
    add_check(
        "observability_validate_script",
        "observability",
        "validate-observability-local.sh",
        "skip",
        "medium",
        "script não existe",
        "Adicione a validação automática de observabilidade local.",
        write_log("observability_validate_script", "script missing\n"),
    )
obs_artifacts = sorted((ROOT / "artifacts").glob("**/validate-observability-local.sh.log"))
add_check(
    "observability_validation_artifacts",
    "observability",
    "Artifacts de validação detectados",
    "pass" if obs_artifacts else "skip",
    "low",
    f"artefatos encontrados={len(obs_artifacts)}",
    "Gere artefatos de observabilidade com a suíte de validação local.",
    write_log("observability_validation_artifacts", "\n".join(str(item) for item in obs_artifacts) + ("\n" if obs_artifacts else "")),
)

models_dir = ROOT / "models"
gguf_found = sorted(models_dir.glob("*.gguf")) if models_dir.exists() else []
add_check(
    "models_dir_exists",
    "models",
    "Diretório models/ existe",
    "pass" if models_dir.exists() else "warn",
    "medium",
    f"models_dir={models_dir.exists()}",
    "Crie o diretório `models/` ou aponte o ambiente para a localização correta dos modelos locais.",
    write_log("models_dir_exists", f"{models_dir}\nexists={models_dir.exists()}\n"),
)
add_check(
    "models_gguf_detected_not_versioned",
    "models",
    "Arquivos .gguf detectados mas não versionados",
    "pass" if not tracked_gguf_lines else "fail",
    "critical",
    f"gguf locais detectados={len(gguf_found)}; versionados={len(tracked_gguf_lines)}",
    "Mantenha modelos locais fora do Git e confirme o ignore para .gguf.",
    write_log("models_gguf_detected_not_versioned", "\n".join([str(item) for item in gguf_found] + tracked_gguf_lines) + ("\n" if gguf_found or tracked_gguf_lines else "")),
)
add_check(
    "models_registered_in_api",
    "models",
    "Modelos registrados em /v1/models",
    "pass" if models_status == 200 and len(models_list) > 0 else "fail",
    "critical",
    f"modelos retornados={len(models_list)}",
    "Registre pelo menos um modelo ativo acessível para clientes locais.",
    models_log,
)
backend_online = False
backend_detail = "status endpoint indisponível"
if status_body:
    try:
        status_json = json.loads(status_body)
        components = status_json.get("components", {})
        backend_detail = f"inference_plane={components.get('inference_plane')} models_active={components.get('models_active')}"
        backend_online = components.get("inference_plane") == "online"
    except Exception:  # noqa: BLE001
        pass
add_check(
    "models_backend_online_reported",
    "models",
    "Backend online/offline reportado",
    "pass" if backend_online else "fail",
    "critical",
    backend_detail,
    "Recupere o backend de inferência e a integração com o control-plane.",
    status_log,
)

totals = {
    "pass": sum(1 for item in checks if item.status == "pass"),
    "warn": sum(1 for item in checks if item.status == "warn"),
    "fail": sum(1 for item in checks if item.status == "fail"),
    "skip": sum(1 for item in checks if item.status == "skip"),
    "critical_failures": sum(1 for item in checks if item.status == "fail" and item.severity == "critical"),
}

high_failures = [item for item in checks if item.status == "fail" and item.severity == "high"]
any_nonoptional_skip = any(item.status == "skip" and item.id not in OPTIONAL_SKIP_IDS for item in checks)
if totals["critical_failures"] > 0:
    score = "NOT_READY"
elif high_failures:
    score = "READY_WITH_WARNINGS"
elif totals["fail"] > 0 or totals["warn"] > 0 or any_nonoptional_skip:
    score = "READY_WITH_WARNINGS"
elif totals["skip"] > 0:
    score = "READY"
else:
    score = "READY"

critical_failures = [item for item in checks if item.status == "fail" and item.severity == "critical"]
warnings = [item for item in checks if item.status == "warn"]
skips = [item for item in checks if item.status == "skip"]
recommendations = []
for item in checks:
    if item.status in {"fail", "warn"} and item.remediation not in recommendations:
        recommendations.append(item.remediation)
recommendations = recommendations[:10]

report = {
    "generated_at": generated_at,
    "version": version,
    "git_branch": git_branch,
    "git_commit": git_commit,
    "git_status_clean": git_status_clean,
    "base_url": BASE_URL,
    "score": score,
    "totals": totals,
    "checks": [item.__dict__ for item in checks],
    "artifacts": {
        "report_md": str(REPORT_MD),
        "report_json": str(REPORT_JSON),
        "logs_dir": str(LOGS_DIR),
    },
}

def render_markdown(current_score: str, current_checks: list[CheckRecord]) -> str:
    current_critical_failures = [item for item in current_checks if item.status == "fail" and item.severity == "critical"]
    current_warnings = [item for item in current_checks if item.status == "warn"]
    current_skips = [item for item in current_checks if item.status == "skip"]
    current_recommendations = []
    for item in current_checks:
        if item.status in {"fail", "warn"} and item.remediation not in current_recommendations:
            current_recommendations.append(item.remediation)
    current_recommendations = current_recommendations[:10]

    md_lines = [
        "# Production Readiness Report Local",
        "",
        f"**Score final:** `{current_score}`",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Version: `{version}`",
        f"- Branch: `{git_branch}`",
        f"- Commit: `{git_commit}`",
        f"- Git status clean: `{str(git_status_clean).lower()}`",
        f"- Base URL: `{BASE_URL}`",
        "",
        "## Tabela de checks",
        "",
        "| ID | Categoria | Titulo | Status | Severidade | Evidencia |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in current_checks:
        md_lines.append(
            f"| `{item.id}` | `{item.category}` | {item.title} | `{item.status}` | `{item.severity}` | `{item.evidence}` |"
        )

    md_lines.extend([
        "",
        "## Falhas criticas",
        "",
    ])
    if current_critical_failures:
        for item in current_critical_failures:
            md_lines.append(f"- `{item.id}`: {item.details}. Remediacao: {item.remediation}")
    else:
        md_lines.append("- Nenhuma.")

    md_lines.extend([
        "",
        "## Warnings",
        "",
    ])
    if current_warnings:
        for item in current_warnings:
            md_lines.append(f"- `{item.id}`: {item.details}. Remediacao: {item.remediation}")
    else:
        md_lines.append("- Nenhum.")

    md_lines.extend([
        "",
        "## Skips opcionais",
        "",
    ])
    if current_skips:
        for item in current_skips:
            md_lines.append(f"- `{item.id}`: {item.details}")
    else:
        md_lines.append("- Nenhum.")

    md_lines.extend([
        "",
        "## Recomendacoes",
        "",
    ])
    if current_recommendations:
        for item in current_recommendations:
            md_lines.append(f"- {item}")
    else:
        md_lines.append("- Nenhuma.")

    md_lines.extend([
        "",
        "## Comandos para reproduzir",
        "",
        "```bash",
        "make production-readiness",
        f"./scripts/dev/production-readiness-local.sh --base-url {BASE_URL}",
        f"./scripts/dev/production-readiness-local.sh --base-url {BASE_URL} --skip-heavy",
        "./scripts/validators/check-secrets.sh --all",
        "```",
        "",
        "## Fora do escopo",
        "",
        "- PSP real",
        "- PIX real",
        "- DNS externo",
        "- HTTPS obrigatorio",
        "- cloud obrigatoria",
        "",
    ])
    return "\n".join(md_lines) + "\n"

REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
REPORT_MD.write_text(render_markdown(score, checks), encoding="utf-8")

artifact_scan = []
for artifact in [REPORT_MD, REPORT_JSON, *sorted(LOGS_DIR.glob("*"))]:
    if artifact.is_file():
        artifact_scan.append(artifact.read_text(encoding="utf-8", errors="replace"))
artifact_text = "\n".join(artifact_scan)
has_secret_leak = any(
    re.search(pattern, artifact_text)
    for pattern in [
        r"sk-[A-Za-z0-9_-]{10,}",
        r"X-Admin-Token:\s*[^\[]",
        r"Authorization:\s*Bearer\s+[^\[]",
    ]
)
for item in checks:
    if item.id == "security_logs_without_full_keys":
        item.status = "fail" if has_secret_leak else "pass"
        item.details = "segredo detectado em artifacts/logs" if has_secret_leak else "nenhum segredo detectado em report/logs gerados"
        item.evidence = write_log("security_logs_without_full_keys", "artifact scan complete\n")
        break

totals = {
    "pass": sum(1 for item in checks if item.status == "pass"),
    "warn": sum(1 for item in checks if item.status == "warn"),
    "fail": sum(1 for item in checks if item.status == "fail"),
    "skip": sum(1 for item in checks if item.status == "skip"),
    "critical_failures": sum(1 for item in checks if item.status == "fail" and item.severity == "critical"),
}

# Consider item.optional for scoring
for item in checks:
    if item.id in OPTIONAL_SKIP_IDS or item.id in OPTIONAL_WARN_IDS:
        item.optional = True

score_relevant_warns = sum(1 for item in checks if item.status == "warn" and not item.optional)
score_relevant_fails = sum(1 for item in checks if item.status == "fail" and not item.optional)
score_relevant_skips = sum(1 for item in checks if item.status == "skip" and not item.optional)
high_failures = [item for item in checks if item.status == "fail" and item.severity == "high" and not item.optional]

if totals["critical_failures"] > 0:
    score = "NOT_READY"
elif high_failures:
    score = "READY_WITH_WARNINGS"
elif score_relevant_fails > 0 or score_relevant_warns > 0 or score_relevant_skips > 0:
    score = "READY_WITH_WARNINGS"
else:
    score = "READY"
report["score"] = score
report["totals"] = totals
report["checks"] = [item.__dict__ for item in checks]
REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
REPORT_MD.write_text(render_markdown(score, checks), encoding="utf-8")

cleanup_created_client()
PY

# Redact the report directory
echo "Redacting production readiness artifacts..."
./scripts/backup/redact-local-sensitive-artifacts.sh --path "${RUN_DIR}" --in-place

# Friendly output
if [[ $? -eq 0 ]]; then
    FINAL_SCORE=$(python3 -c "import json; print(json.load(open('${REPORT_JSON}'))['score'])")
    if [[ "${FINAL_SCORE}" == "READY" ]]; then
        operator_success "Sistema pronto para produção local! Score: READY"
    elif [[ "${FINAL_SCORE}" == "READY_WITH_WARNINGS" ]]; then
        operator_warning "READY_DEGRADED" "Sistema pronto, mas com avisos." "Revise os avisos no relatório em ${REPORT_MD}"
    else
        operator_error "VALIDATION_FAILED" "O sistema NÃO está pronto para produção local." "Corrija as falhas críticas apontadas no relatório em ${REPORT_MD}"
    fi
else
    operator_error "VALIDATION_FAILED" "Falha ao gerar o relatório de prontidão." "Verifique se o sistema está acessível e se as dependências estão instaladas."
fi

add_next_step "Revise o relatório completo em: ${REPORT_MD}"
add_next_step "Execute 'make health' para monitoramento contínuo."
print_next_steps

if [[ "${JSON_ONLY}" == "true" ]]; then
  cat "${REPORT_JSON}"
fi

if [[ "${STRICT}" == "true" ]]; then
  python3 - "${REPORT_JSON}" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    score = json.load(handle)["score"]
raise SystemExit(0 if score == "READY" else 1)
PY
fi
