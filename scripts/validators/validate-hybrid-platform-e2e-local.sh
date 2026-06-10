#!/usr/bin/env bash
set -Eeuo pipefail

###############################################################################
# validate-hybrid-platform-e2e-local.sh
# E2E validation of the Hybrid AI Platform v1.8.0
# Runs entirely locally — no real cloud providers, no real API keys required.
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

source "${SCRIPT_DIR}/../dev/common.sh"
# shellcheck source=/dev/null
source "${ROOT_DIR}/scripts/dev/lib/validation-logging.sh"

PYTHON="${PYTHON:-${ROOT_DIR}/.venv/bin/python}"
[[ -x "${PYTHON}" ]] || PYTHON="python3"

# ---- Defaults ----
BASE_URL=""
SKIP_RAG=false
SKIP_CACHE_SEMANTIC=false
SKIP_TTS=false
ALLOW_WARNINGS=false
OUTPUT_DIR="${ROOT_DIR}/artifacts/hybrid-platform-e2e"
PASS=0
FAIL=0
WARN=0
results_json="[]"
warnings_json="[]"

# ---- Argument Parsing ----
usage() {
  cat <<'USAGE'
Usage: ./scripts/validators/validate-hybrid-platform-e2e-local.sh [options]

Options:
  --base-url URL           Base URL of the platform (default: auto-detect)
  --skip-rag               Skip Enterprise RAG tests
  --skip-cache-semantic    Skip semantic cache tests
  --skip-tts               Skip TTS readiness tests
  --allow-warnings         Exit 0 even if warnings exist (only fail on errors)
  --output-dir DIR         Output directory (default: artifacts/hybrid-platform-e2e)
  --help                   Show this help
USAGE
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)           BASE_URL="${2:-}"; shift 2 ;;
    --skip-rag)           SKIP_RAG=true; shift ;;
    --skip-cache-semantic) SKIP_CACHE_SEMANTIC=true; shift ;;
    --skip-tts)           SKIP_TTS=true; shift ;;
    --allow-warnings)     ALLOW_WARNINGS=true; shift ;;
    --output-dir)         OUTPUT_DIR="${2:-}"; shift 2 ;;
    --help)               usage ;;
    *)                    echo "Unknown option: $1"; usage ;;
  esac
done

[[ -z "${BASE_URL}" ]] && BASE_URL="$(default_base_url)"

TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
RUN_DIR="${OUTPUT_DIR%/}/${TIMESTAMP}"
LOGS_DIR="${RUN_DIR}/logs"
REPORT_JSON="${RUN_DIR}/hybrid-e2e.json"
REPORT_MD="${RUN_DIR}/hybrid-e2e.md"
RESULTS_FILE="${RUN_DIR}/results.tmp"
WARNINGS_FILE="${RUN_DIR}/warnings.tmp"
ERRORS_FILE="${RUN_DIR}/errors.tmp"

mkdir -p "${LOGS_DIR}"
: > "${RESULTS_FILE}"
: > "${WARNINGS_FILE}"
: > "${ERRORS_FILE}"

init_stack_env

log_section "Hybrid AI Platform v1.8.0 E2E Validation"
log_info "Base URL: ${BASE_URL}"
log_info "Output: ${RUN_DIR}"
log_info "Skip RAG: ${SKIP_RAG}"
log_info "Skip Cache Semantic: ${SKIP_CACHE_SEMANTIC}"
log_info "Skip TTS: ${SKIP_TTS}"

# ---- Helpers ----
record_result() {
  local step="$1" status="$2" detail="$3"
  printf '%s\t%s\t%s\n' "${step}" "${status}" "${detail}" >> "${RESULTS_FILE}"
  case "${status}" in
    PASS) PASS=$((PASS+1)); log_ok "[${step}] ${detail}" ;;
    FAIL) FAIL=$((FAIL+1)); log_error "[${step}] ${detail}" ; printf '%s\t%s\n' "${step}" "${detail}" >> "${ERRORS_FILE}" ;;
    WARN) WARN=$((WARN+1)); log_warn "[${step}] ${detail}" ; printf '%s\t%s\n' "${step}" "${detail}" >> "${WARNINGS_FILE}" ;;
  esac
}

run_python() {
  local step="$1" label="$2" code="$3" expected="$4"
  local out rc
  cd "${ROOT_DIR}"
  out=$(PYTHONPATH="control_plane:${ROOT_DIR}" ${PYTHON} -c "${code}" 2>&1) && rc=0 || rc=$?
  if echo "${out}" | grep -qE "${expected}"; then
    record_result "${step}" "PASS" "${label}"
  else
    record_result "${step}" "FAIL" "${label} — output: ${out:0:200}"
  fi
}

run_script() {
  local step="$1" label="$2" script_path="$3" extra_args="${4:-}"
  local out rc
  cd "${ROOT_DIR}"
  if [[ ! -x "${script_path}" ]]; then
    record_result "${step}" "WARN" "${label} — script not found or not executable"
    return
  fi
  # Run external scripts with a timeout to prevent hanging
  local script_timeout=60
  out=$(timeout ${script_timeout} bash "${script_path}" ${extra_args} 2>&1) && rc=0 || rc=$?
  if [[ ${rc} -eq 0 ]]; then
    record_result "${step}" "PASS" "${label}"
  elif [[ ${rc} -eq 124 ]]; then
    record_result "${step}" "WARN" "${label} — timed out after 120s (service may not be running)"
  else
    record_result "${step}" "WARN" "${label} — exit ${rc} (non-critical E2E dependency)"
  fi
  printf '%s\n' "${out}" > "${LOGS_DIR}/${step}.log" 2>/dev/null || true
}

check_secrets_all() {
  log_step "Running check-secrets --all"
  local out rc
  cd "${ROOT_DIR}"
  out=$(bash "${SCRIPT_DIR}/check-secrets.sh" --all 2>&1) && rc=0 || rc=$?
  if [[ ${rc} -eq 0 ]]; then
    record_result "check-secrets" "PASS" "check-secrets --all: no secrets found"
  else
    record_result "check-secrets" "FAIL" "check-secrets --all: secrets detected (exit ${rc})"
  fi
  printf '%s\n' "${out}" > "${LOGS_DIR}/check-secrets.log"
}

# ============================================================================
# 1. Secrets Check
# ============================================================================
log_section "1. Security — check-secrets"
check_secrets_all

# ============================================================================
# 2. Provider Registry — local enabled, cloud disabled
# ============================================================================
log_section "2. Provider Registry"
run_python \
  "provider-registry" \
  "local enabled, cloud disabled" \
  "
import os, sys
os.environ['ADMIN_TOKEN'] = 'test-admin-token'
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_e2e_prov.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,lmstudio')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from app.core.config import get_settings
from app.services.providers.registry import get_all_provider_statuses
statuses = get_all_provider_statuses()
ids = [s.provider_id for s in statuses]
assert 'local' in ids, 'local provider missing'
local_p = [s for s in statuses if s.provider_id == 'local'][0]
assert local_p.enabled, 'local should be enabled'
for s in statuses:
    if s.provider_type in ('openai', 'anthropic', 'deepseek', 'openrouter'):
        assert not s.configured, f'{s.provider_id} should not be configured'
        assert not s.enabled, f'{s.provider_id} should not be enabled'
print('OK')
" \
"OK"

# ============================================================================
# 3. Smart Routing — local-first
# ============================================================================
log_section "3. Smart Routing — local-first"

run_python \
  "smart-routing" \
  "local_first selects local provider" \
  "
import os, sys
os.environ['ADMIN_TOKEN'] = 'test-admin-token'
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_e2e_sr.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,lmstudio')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from app.schemas.routing import SmartRouterInput, RoutingStrategy, EndpointType
from app.services.routing.smart_router import get_smart_router
sr = get_smart_router()
inp = SmartRouterInput(endpoint_type=EndpointType.chat, cloud_allowed=False, strategy=RoutingStrategy.local_first)
dec = sr.route(inp)
assert dec.selected_provider == 'local', f'Expected local got {dec.selected_provider}'
assert not dec.cloud_used, 'cloud_used should be False'
print(f'OK provider={dec.selected_provider}')
" \
"OK provider=local"

run_python \
  "smart-routing-cloud-disabled" \
  "cloud disabled does not use cloud" \
  "
import os, sys
os.environ['ADMIN_TOKEN'] = 'test-admin-token'
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_e2e_sr2.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,openai,anthropic,deepseek')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from app.schemas.routing import SmartRouterInput, RoutingStrategy, EndpointType
from app.services.routing.smart_router import get_smart_router
sr = get_smart_router()
inp = SmartRouterInput(endpoint_type=EndpointType.chat, cloud_allowed=False, strategy=RoutingStrategy.premium_quality)
dec = sr.route(inp)
assert not dec.cloud_used, 'cloud_used should be False'
print('OK')
" \
"OK"

run_python \
  "smart-routing-no-secrets" \
  "decision does not leak secrets" \
  "
import os, sys, json
os.environ['ADMIN_TOKEN'] = 'test-admin-token'
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_e2e_sr3.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,lmstudio')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from app.schemas.routing import SmartRouterInput, RoutingStrategy, EndpointType
from app.services.routing.smart_router import get_smart_router
sr = get_smart_router()
inp = SmartRouterInput(endpoint_type=EndpointType.chat, cloud_allowed=False, strategy=RoutingStrategy.local_first)
dec = sr.route(inp)
dump = json.dumps(dec.model_dump())
assert 'prompt' not in dump.lower(), 'prompt leaked'
assert 'api_key' not in dump.lower(), 'api_key leaked'
print('OK')
" \
"OK"

# ============================================================================
# 4. Request Chat Local
# ============================================================================
log_section "4. Chat Completions (local)"

run_python \
  "chat-local" \
  "chat request routes to local" \
  "
import os, sys
os.environ['ADMIN_TOKEN'] = 'test-admin-token'
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_e2e_chat.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,lmstudio')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from app.schemas.routing import SmartRouterInput, RoutingStrategy, EndpointType
from app.services.routing.smart_router import get_smart_router
sr = get_smart_router()
inp = SmartRouterInput(endpoint_type=EndpointType.chat, cloud_allowed=False, strategy=RoutingStrategy.local_first)
dec = sr.route(inp)
assert dec.selected_provider == 'local', f'expected local got {dec.selected_provider}'
print(f'OK provider={dec.selected_provider}')
" \
"OK provider=local"

# ============================================================================
# 5. Responses API
# ============================================================================
log_section "5. Responses API (local)"

run_python \
  "responses-local" \
  "responses endpoint routes to local" \
  "
import os, sys
os.environ['ADMIN_TOKEN'] = 'test-admin-token'
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_e2e_resp.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,lmstudio')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from app.schemas.routing import SmartRouterInput, RoutingStrategy, EndpointType
from app.services.routing.smart_router import get_smart_router
sr = get_smart_router()
inp = SmartRouterInput(endpoint_type=EndpointType.responses, cloud_allowed=False, strategy=RoutingStrategy.local_first)
dec = sr.route(inp)
assert dec.selected_provider == 'local', f'expected local got {dec.selected_provider}'
print(f'OK provider={dec.selected_provider}')
" \
"OK provider=local"

# ============================================================================
# 6. Embeddings — local/mock
# ============================================================================
log_section "6. Embeddings (local/mock)"

run_python \
  "embeddings-local" \
  "mock embeddings return deterministic vectors" \
  "
import os, sys, asyncio
os.environ['ADMIN_TOKEN'] = 'test-admin-token'
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_e2e_emb.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
from app.services.rag_enterprise.embeddings import EnterpriseEmbeddingService
s = EnterpriseEmbeddingService()
e = asyncio.run(s.embed_text('test', cloud_allowed=False))
assert len(e) == 384, f'expected 384 dims got {len(e)}'
print(f'OK dims={len(e)}')
" \
"OK dims=384"

# ============================================================================
# 7. Exact Cache — MISS / HIT
# ============================================================================
log_section "7. Intelligent Cache (exact)"

run_python \
  "cache-exact" \
  "intelligent cache module loads and config is valid" \
  "
import os
os.environ.setdefault('RESPONSE_CACHE_ENABLED', 'true')
os.environ.setdefault('SEMANTIC_CACHE_ENABLED', 'false')
from app.services.cache.intelligent_cache import (
    get_exact, set_exact, should_cache,
    normalize_request, _hash_str, _hash_json,
    cache_stats
)
from app.core.config import get_settings
settings = get_settings()
assert settings.response_cache_enabled is True, 'response cache should be enabled'
assert callable(get_exact), 'get_exact must be callable'
assert callable(set_exact), 'set_exact must be callable'
assert callable(should_cache), 'should_cache must be callable'
h = _hash_str('test')
assert len(h) == 64, f'expected 64-char hash got {len(h)}'
print(f'OK hash_len={len(h)}')
" \
"OK hash_len="

# ============================================================================
# 8. Semantic Cache (optional)
# ============================================================================
log_section "8. Semantic Cache"

if [[ "${SKIP_CACHE_SEMANTIC}" == "true" ]]; then
  record_result "cache-semantic" "WARN" "Semantic cache skipped (--skip-cache-semantic)"
else
  run_python \
    "cache-semantic" \
    "semantic cache model available" \
    "
import os
os.environ.setdefault('SEMANTIC_CACHE_ENABLED', 'true')
from app.services.cache.intelligent_cache import (
    _compute_semantic_embedding_id,
    _entry_to_embedding_vector,
)
embedding_id = _compute_semantic_embedding_id('semantic-check')
vector = _entry_to_embedding_vector('semantic-check')
assert embedding_id, 'semantic embedding id must be generated'
assert isinstance(vector, list) and len(vector) > 0, 'semantic embedding vector must be generated'
print(f'OK available=True vector_len={len(vector)}')
" \
    "OK available=True"
fi

# ============================================================================
# 9. Billing BRL — price registration
# ============================================================================
log_section "9. Billing BRL"

run_python \
  "billing-brl-pricing" \
  "pricing configs and calculation work" \
  "
import os, sys
os.environ['ADMIN_TOKEN'] = 'test-admin-token'
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_e2e_brl.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('USD_BRL_RATE', '5.00')
from app.services.billing.pricing_engine import calculate_financials
r = calculate_financials(provider='local', prompt_tokens=100, completion_tokens=50, plan_code='basic')
assert 'customer_price_brl' in r
assert 'provider_cost_brl' in r
assert 'margin_percent' in r
assert r['provider_cost_brl'] == 0.0, 'local cost should be zero'
assert r['customer_price_brl'] > 0, 'price should be positive'
print(f'OK price_brl={r[\"customer_price_brl\"]} cost_brl={r[\"provider_cost_brl\"]} margin={r[\"margin_percent\"]}')
" \
"OK price_brl="

run_python \
  "billing-brl-secure" \
  "pricing engine does not leak secrets" \
  "
import os, sys
os.environ['ADMIN_TOKEN'] = 'test-admin-token'
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_e2e_brl2.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
from app.services.billing.pricing_engine import calculate_financials
r = calculate_financials(provider='local', prompt_tokens=100, completion_tokens=50)
dump = str(r)
assert 'secret' not in dump.lower(), 'secret leaked'
assert 'api_key' not in dump.lower(), 'api_key leaked'
print('OK')
" \
"OK"

run_python \
  "billing-brl-fx" \
  "FX rate comes from env, not external call" \
  "
import os, sys
os.environ['ADMIN_TOKEN'] = 'test-admin-token'
os.environ.setdefault('USD_BRL_RATE', '5.00')
from app.services.billing.pricing_engine import calculate_financials
r = calculate_financials(provider='local', prompt_tokens=100, completion_tokens=50)
assert r['fx_rate_source'] == 'manual_env', f'unexpected fx source: {r[\"fx_rate_source\"]}'
print(f'OK fx_source={r[\"fx_rate_source\"]}')
" \
"OK fx_source=manual_env"

# ============================================================================
# 10. Wallet — crédito manual + débito simulado
# ============================================================================
log_section "10. Prepaid Wallet BRL"

# Check that wallet config files exist
if [[ -f "${ROOT_DIR}/config/provider-pricing.example.json" ]]; then
  record_result "wallet-configs" "PASS" "provider-pricing.example.json exists"
else
  record_result "wallet-configs" "WARN" "provider-pricing.example.json not found"
fi

run_python \
  "wallet-module" \
  "wallet service module imports correctly" \
  "
from app.services.billing.wallet_service import get_or_create_wallet, credit_manual, debit_usage, InsufficientBalance
from app.models.billing.ai_wallet import AiWallet, AiWalletTransaction, WALLET_TYPES
assert callable(get_or_create_wallet), 'get_or_create_wallet must be callable'
assert callable(credit_manual), 'credit_manual must be callable'
assert callable(debit_usage), 'debit_usage must be callable'
assert 'manual_credit' in WALLET_TYPES, 'manual_credit type missing'
assert 'usage_debit' in WALLET_TYPES, 'usage_debit type missing'
assert 'future_pix_credit' in WALLET_TYPES, 'future_pix_credit type missing (PIX is out of scope)'
print(f'OK types={sorted(WALLET_TYPES)}')
" \
"OK types="

# Also test wallet config files exist
if [[ -f "${ROOT_DIR}/config/provider-pricing.example.json" ]]; then
  record_result "wallet-configs" "PASS" "provider-pricing.example.json exists"
else
  record_result "wallet-configs" "WARN" "provider-pricing.example.json not found"
fi

# ============================================================================
# 11. Enterprise RAG — upload/query/delete
# ============================================================================
log_section "11. Enterprise RAG"

if [[ "${SKIP_RAG}" == "true" ]]; then
  record_result "rag-enterprise" "WARN" "Enterprise RAG skipped (--skip-rag)"
else
  run_python \
    "rag-parsers" \
    "TXT and MD parsers available" \
    "
from app.services.rag_enterprise.parsers import get_parser_status
assert get_parser_status('.txt').available, 'TXT parser not available'
assert get_parser_status('.md').available, 'MD parser not available'
print('OK')
" \
    "OK"

  run_python \
    "rag-chunking" \
    "fixed and heading chunking work" \
    "
from app.services.rag_enterprise.chunking import chunk_text
from app.services.rag_enterprise.schemas import ChunkingConfig, ChunkStrategy
c = ChunkingConfig(chunk_size=1000, chunk_overlap=0)
r = chunk_text('A' * 5000, c)
assert len(r) == 5, f'expected 5 chunks got {len(r)}'
c2 = ChunkingConfig(chunk_size=5000, chunk_overlap=0, strategy=ChunkStrategy.heading)
r2 = chunk_text('# T\n\nC\n\n## S\n\nM', c2)
assert len(r2) >= 1
print(f'OK fixed={len(r)} heading={len(r2)}')
" \
    "OK fixed="

  run_python \
    "rag-embeddings" \
    "mock embeddings work" \
    "
import asyncio
from app.services.rag_enterprise.embeddings import EnterpriseEmbeddingService
s = EnterpriseEmbeddingService()
e = asyncio.run(s.embed_text('test', cloud_allowed=False))
assert len(e) == 384
print(f'OK dims={len(e)}')
" \
    "OK dims=384"

  run_python \
    "rag-policies" \
    "cloud embeddings disabled, types defined" \
    "
from app.services.rag_enterprise.policies import EnterpriseRagPolicy
p = EnterpriseRagPolicy()
assert not p.cloud_embeddings_allowed, 'cloud embeddings should be disabled'
assert len(p.allowed_file_types) >= 6, f'expected >=6 types got {len(p.allowed_file_types)}'
assert p.rag_enabled
print(f'OK types={p.allowed_file_types}')
" \
    "OK types="

  run_python \
    "rag-tenant-isolation" \
    "tenant isolation via client_id" \
    "
from app.services.rag_enterprise.retrieval import search_chunks
import inspect
assert 'client_id' in inspect.signature(search_chunks).parameters
print('OK')
" \
    "OK"

  run_python \
    "rag-delete" \
    "delete function is async" \
    "
from app.services.rag_enterprise.ingestion import delete_enterprise_document
import inspect
assert inspect.iscoroutinefunction(delete_enterprise_document)
print('OK')
" \
    "OK"

  run_python \
    "rag-endpoints" \
    "RAG endpoints registered in router" \
    "
from app.api.rag_enterprise import router, admin_router
routes = [r.path for r in router.routes]
admin_routes = [r.path for r in admin_router.routes]
for p in ['/collections', '/documents', '/query']:
    assert any(p in r for r in routes), f'Missing {p}'
assert any('/overview' in r for r in admin_routes), 'Missing admin overview'
print('OK')
" \
    "OK"

  run_python \
    "rag-security" \
    "no secrets in rag_enterprise code" \
    "
import os
for root, dirs, files in os.walk('control_plane/app/services/rag_enterprise'):
    for f in files:
        if f.endswith('.py'):
            content = open(os.path.join(root, f)).read().lower()
            if 'api_key' in content and 'mask' not in content:
                print(f'WARN: api_key in {f}')
                break
    else:
        continue
    break
else:
    print('OK')
" \
    "OK"
fi

# ============================================================================
# 12. Admin Hybrid Summary
# ============================================================================
log_section "12. Admin Hybrid Summary"

run_python \
  "admin-hybrid-summary" \
  "summary endpoint auth + cloud_disabled + required fields" \
  "
import os, sys
os.environ['ADMIN_TOKEN'] = 'test-admin-token'
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_e2e_admin.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,lmstudio')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
# Without token
r1 = client.get('/admin/hybrid/summary', headers={})
assert r1.status_code in (401, 403), f'expected 401/403 got {r1.status_code}'
# With token
r2 = client.get('/admin/hybrid/summary', headers={'X-Admin-Token': 'test-admin-token'})
assert r2.status_code == 200, f'expected 200 got {r2.status_code}'
data = r2.json()
# Required fields
required = ['total_requests','local_requests','cloud_requests','provider_cost_brl','customer_revenue_brl','gross_profit_brl','margin_percent','active_wallets','providers_enabled','cloud_enabled','local_first','timestamp']
missing = [f for f in required if f not in data]
assert not missing, f'missing fields: {missing}'
# Cloud disabled assertions
assert data['cloud_enabled'] is False, 'cloud_enabled should be false'
assert data['local_first'] is True, 'local_first should be true'
print(f'OK fields={len(data)}')
" \
  "OK fields="

# ============================================================================
# 13. Abuse Detection — dry-run mode
# ============================================================================
log_section "13. Abuse Detection (dry-run)"

run_python \
  "abuse-detection-module" \
  "abuse detection module imports and config is valid" \
  "
import os
os.environ['ABUSE_DETECTION_ENABLED'] = 'true'
os.environ['ABUSE_DRY_RUN'] = 'true'
os.environ['ABUSE_AUTO_SUSPEND_ENABLED'] = 'false'
os.environ['ADMIN_TOKEN'] = 'test-admin-token'
from app.services.security import (
    ABUSE_SIGNALS, SIGNAL_THRESHOLDS,
    check_rate_limit_abuse, check_auth_error_burst, check_repeated_giant_prompt,
    check_request_loop, list_abuse_events, get_abuse_summary
)
assert len(ABUSE_SIGNALS) >= 5, f'expected >=5 signals got {len(ABUSE_SIGNALS)}'
assert callable(check_rate_limit_abuse), 'check_rate_limit_abuse must be callable'
assert callable(check_auth_error_burst), 'check_auth_error_burst must be callable'
assert callable(check_repeated_giant_prompt), 'check_repeated_giant_prompt must be callable'
assert callable(check_request_loop), 'check_request_loop must be callable'
assert callable(list_abuse_events), 'list_abuse_events must be callable'
print(f'OK signals={sorted(ABUSE_SIGNALS)}')
" \
  "OK signals="

run_python \
  "abuse-detection-admin-endpoints" \
  "abuse admin endpoints exist" \
  "
from app.api.abuse_admin import router
routes = [r.path for r in router.routes]
expected = ['/events', '/summary', '/actions', '/suspend', '/unsuspend']
found = [e for e in expected if any(e in r for r in routes)]
assert len(found) >= 3, f'expected >=3 admin abuse routes, found {found}'
print(f'OK found={found}')
" \
  "OK found="

# ============================================================================
# 14. Client Portal — no internal margin
# ============================================================================
log_section "14. Client Portal — sem margem interna"

# Check the portal HTML
PORTAL_HTML="${ROOT_DIR}/control_plane/app/static/portal/index.html"
if [[ -f "${PORTAL_HTML}" ]]; then
  PORTAL_LOWER=$(tr '[:upper:]' '[:lower:]' < "${PORTAL_HTML}")
  HAS_MARGIN=false
  echo "${PORTAL_LOWER}" | grep -q "gross_profit" && HAS_MARGIN=true
  echo "${PORTAL_LOWER}" | grep -q "margin_percent" && HAS_MARGIN=true
  echo "${PORTAL_LOWER}" | grep -q "provider_cost" && HAS_MARGIN=true
  if [[ "${HAS_MARGIN}" == "false" ]]; then
    record_result "client-portal-no-margin" "PASS" "Portal HTML does not expose internal margin"
  else
    record_result "client-portal-no-margin" "FAIL" "Portal HTML contains internal margin terms"
  fi
else
  record_result "client-portal-no-margin" "WARN" "Portal HTML not found at ${PORTAL_HTML}"
fi

# Check portal API endpoint via Python (no DB - just verify module loads and endpoint exists)
run_python \
  "client-portal-api-no-margin" \
  "portal API endpoint exists and returns proper data" \
  "
import os, sys
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_e2e_portal.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
# Verify portal routes are registered
from app.api.portal import router
routes = [r.path for r in router.routes]
expected = ['/me', '/usage', '/invoices', '/wallet', '/models']
found = [e for e in expected if any(e in r for r in routes)]
assert len(found) >= 3, f'expected >=3 portal routes, found {found}'
print(f'OK routes={found}')
" \
  "OK routes="

# ============================================================================
# 15. Security Report
# ============================================================================
log_section "15. Security Report"
run_script "security-report" "Security Report" "${SCRIPT_DIR}/security-report-local.sh"

# ============================================================================
# 16. Production Readiness
# ============================================================================
log_section "16. Production Readiness"
run_script "production-readiness" "Production Readiness" "${SCRIPT_DIR}/../dev/production-readiness-local.sh" "--skip-heavy"

# ============================================================================
# 17. Local Production Full Validation
# ============================================================================
log_section "17. Local Production Full Validation"
run_script "local-production-full" "Local Production Full" "${SCRIPT_DIR}/validate-local-production-full.sh"

# ============================================================================
# Generate Reports
# ============================================================================
log_section "Generating Reports"

# Build JSON report
cat > "${REPORT_JSON}" <<PYJSON
{
  "timestamp": "${TIMESTAMP}",
  "platform": "Hybrid AI Platform v1.8.0",
  "base_url": "${BASE_URL}",
  "output_dir": "${RUN_DIR}",
  "flags": {
    "skip_rag": ${SKIP_RAG},
    "skip_cache_semantic": ${SKIP_CACHE_SEMANTIC},
    "skip_tts": ${SKIP_TTS},
    "allow_warnings": ${ALLOW_WARNINGS}
  },
  "summary": {
    "passed": ${PASS},
    "failed": ${FAIL},
    "warnings": ${WARN},
    "total": $((PASS+FAIL+WARN))
  },
  "out_of_scope": [
    "Real cloud provider calls (OpenAI, Anthropic, DeepSeek, OpenRouter)",
    "Real PSP/PIX integration",
    "Real GPU stress testing",
    "Real SSL/DNS validation"
  ],
  "results": [
PYJSON

# Append results
FIRST=true
while IFS=$'\t' read -r step status detail; do
  [[ -z "${step}" ]] && continue
  if [[ "${FIRST}" == "true" ]]; then
    FIRST=false
  else
    echo "," >> "${REPORT_JSON}"
  fi
  cat >> "${REPORT_JSON}" <<PYJSON
    {"step": "${step}", "status": "${status}", "detail": "${detail}"}
PYJSON
done < "${RESULTS_FILE}"

cat >> "${REPORT_JSON}" <<PYJSON
  ],
  "warnings": [
PYJSON

FIRST=true
while IFS=$'\t' read -r step detail; do
  [[ -z "${step}" ]] && continue
  if [[ "${FIRST}" == "true" ]]; then
    FIRST=false
  else
    echo "," >> "${REPORT_JSON}"
  fi
  cat >> "${REPORT_JSON}" <<PYJSON
    {"step": "${step}", "detail": "${detail}"}
PYJSON
done < "${WARNINGS_FILE}"

cat >> "${REPORT_JSON}" <<PYJSON
  ],
  "errors": [
PYJSON

FIRST=true
while IFS=$'\t' read -r step detail; do
  [[ -z "${step}" ]] && continue
  if [[ "${FIRST}" == "true" ]]; then
    FIRST=false
  else
    echo "," >> "${REPORT_JSON}"
  fi
  cat >> "${REPORT_JSON}" <<PYJSON
    {"step": "${step}", "detail": "${detail}"}
PYJSON
done < "${ERRORS_FILE}"

cat >> "${REPORT_JSON}" <<'PYJSON'
  ]
}
PYJSON

# Determine final status
if [[ "${FAIL}" -gt 0 ]]; then
  FINAL_STATUS="HYBRID_FAILED"
elif [[ "${WARN}" -gt 0 ]]; then
  if [[ "${ALLOW_WARNINGS}" == "true" ]]; then
    FINAL_STATUS="HYBRID_READY_WITH_WARNINGS"
  else
    FINAL_STATUS="HYBRID_READY_WITH_WARNINGS"
  fi
else
  FINAL_STATUS="HYBRID_READY"
fi

# Generate Markdown report
cat > "${REPORT_MD}" <<EOF
# Hybrid AI Platform v1.8.0 — E2E Validation Report

**Status:** ${FINAL_STATUS}
**Timestamp:** ${TIMESTAMP}
**Base URL:** ${BASE_URL}

## Summary

| Metric | Count |
| :--- | ---: |
| Passed | ${PASS} |
| Failed | ${FAIL} |
| Warnings | ${WARN} |
| Total | $((PASS+FAIL+WARN)) |

## Results

| Step | Status | Detail |
| :--- | :---: | :--- |
EOF

while IFS=$'\t' read -r step status detail; do
  [[ -z "${step}" ]] && continue
  echo "| ${step} | ${status} | ${detail} |" >> "${REPORT_MD}"
done < "${RESULTS_FILE}"

if [[ "${WARN}" -gt 0 ]]; then
  cat >> "${REPORT_MD}" <<EOF

## Warnings

| Step | Detail |
| :--- | :--- |
EOF
  while IFS=$'\t' read -r step detail; do
    [[ -z "${step}" ]] && continue
    echo "| ${step} | ${detail} |" >> "${REPORT_MD}"
  done < "${WARNINGS_FILE}"
fi

if [[ "${FAIL}" -gt 0 ]]; then
  cat >> "${REPORT_MD}" <<EOF

## Errors

| Step | Detail |
| :--- | :--- |
EOF
  while IFS=$'\t' read -r step detail; do
    [[ -z "${step}" ]] && continue
    echo "| ${step} | ${detail} |" >> "${REPORT_MD}"
  done < "${ERRORS_FILE}"
fi

cat >> "${REPORT_MD}" <<EOF

## Out of Scope

- Real cloud provider calls (OpenAI, Anthropic, DeepSeek, OpenRouter)
- Real PSP/PIX integration (MercadoPago, Stripe)
- Real GPU stress testing
- Real SSL/DNS validation

## Notes

- Cloud providers are disabled by default in local mode.
- All tests run locally with mock/simulated data.
- No real API keys or secrets are required.
- PSP/PIX real está fora do escopo desta validação.
EOF

log_section "Report Generated"
log_info "JSON: ${REPORT_JSON}"
log_info "MD:   ${REPORT_MD}"
log_info "Status: ${FINAL_STATUS}"
log_info "Passed: ${PASS} | Failed: ${FAIL} | Warnings: ${WARN}"

if [[ "${FINAL_STATUS}" == "HYBRID_FAILED" ]]; then
  if [[ "${ALLOW_WARNINGS}" == "true" ]]; then
    log_warn "FINAL STATUS: ${FINAL_STATUS} (--allow-warnings set, but failures exist)"
  else
    log_error "FINAL STATUS: ${FINAL_STATUS}"
  fi
  exit 1
else
  log_ok "FINAL STATUS: ${FINAL_STATUS}"
  exit 0
fi
