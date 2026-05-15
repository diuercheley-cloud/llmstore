# Hardware-backed Attestation Runtime (Phase 58)

## Overview
Evolui o placeholder de hardware attestation existente para um runtime de attestation avançado com abstrações TPM/SEV/SGX/VBS placeholders, medição de integridade do runtime, evidence chaining, attested workflow execution e binding criptográfico entre modelo, runtime e workflow determinístico.

**IMPORTANTE**: Esta implementação é **placeholder operational-grade**. Não oferece confidential computing real, nem conformidade formal TPM/SGX/SEV. Sem SaaS externo. Sem armazenamento de prompts/respostas completos.

## Arquitetura

### Modelos (5 tabelas)
- `CommercialRuntimeAttestation` - Attestation principal com runtime_hash, evidence_hash, trust_score, immutable_hash chain
- `CommercialAttestationEvidence` - Evidence chain com signed_evidence, chain_position, previous_evidence_hash
- `CommercialAttestationPolicy` - Políticas de attestation com min_trust_score, allowed_enclave_types, enforcement_mode
- `CommercialRuntimeMeasurement` - Snapshots de medição (runtime_binary, loaded_model, workflow_hash, etc)
- `CommercialAttestationChallenge` - Challenge/response attestation com nonce, replay protection, TTL

### Serviços (4 módulos)
1. **runtime_attestation.py** - Core: create, verify, trust scoring, drift detection, chaining, revocation
2. **attestation_measurements.py** - Snapshots: runtime binaries, loaded models, workflow hashes, policy bundles, routing hashes, environment fingerprints
3. **attestation_challenges.py** - Challenge/response: issue, respond, verify, expire stale, revoke
4. **runtime_integrity.py** - Governance: policy evaluation, block untrusted, sovereign/sensitive tenant enforcement

### Enclave Placeholders
| Mode | Descrição |
|------|-----------|
| `software_attested` | Software-based fingerprint (default) |
| `tpm_placeholder` | TPM 2.0 PCR measurements (placeholder) |
| `sev_placeholder` | AMD SEV-SNP attestation (placeholder) |
| `sgx_placeholder` | Intel SGX enclave (placeholder) |
| `vbs_placeholder` | Hyper-V VBS (placeholder) |

### Componentes Mensurados
- Runtime binary hashes
- Loaded model hashes
- Workflow hashes
- Policy bundle hashes
- Routing hashes
- Environment fingerprint (platform, architecture, python, hostname, pid)

### Criptografia
- `immutable_hash` chain linking cada attestation ao anterior
- `evidence_hash` para verificação de integridade do evidence JSON
- `measurement_chain_hash` para chain de todas as medições
- Nonce aleatório (32 bytes via `secrets.token_hex`) para challenges

## Configuração

```bash
# Ativar runtime attestation
export COMMERCIAL_RUNTIME_ATTESTATION_ENABLED=true
export COMMERCIAL_RUNTIME_ATTESTATION_MODE=enforce

# Tipo de enclave
export COMMERCIAL_RUNTIME_ATTESTATION_ENCLAVE_TYPE=software_attested

# Thresholds
export COMMERCIAL_RUNTIME_ATTESTATION_MIN_TRUST_SCORE=0.5
export COMMERCIAL_RUNTIME_ATTESTATION_MAX_DRIFT_THRESHOLD=0.1
export COMMERCIAL_RUNTIME_ATTESTATION_CHALLENGE_TTL_SECONDS=60
export COMMERCIAL_RUNTIME_ATTESTATION_EVIDENCE_TTL_SECONDS=3600

# Governance
export COMMERCIAL_RUNTIME_ATTESTATION_REQUIRE_FOR_SOVEREIGN=true
export COMMERCIAL_RUNTIME_ATTESTATION_REQUIRE_FOR_SENSITIVE_TENANTS=true
export COMMERCIAL_RUNTIME_ATTESTATION_BLOCK_UNTRUSTED=true
export COMMERCIAL_RUNTIME_ATTESTATION_ENFORCE_ON_STARTUP=true
```

## Endpoints

### Admin
- `GET /admin/attestation/runtime` - Listar attestations
- `GET /admin/attestation/runtime/summary` - Sumário
- `POST /admin/attestation/runtime` - Criar attestation
- `GET /admin/attestation/runtime/{id}` - Detalhe
- `POST /admin/attestation/runtime/{id}/verify` - Verificar
- `POST /admin/attestation/runtime/{id}/drift` - Detectar drift
- `POST /admin/attestation/runtime/{id}/revoke` - Revogar
- `POST /admin/attestation/runtime/{id}/trust-score` - Calcular trust score
- `GET /admin/attestation/evidence` - Listar evidence chain
- `GET /admin/attestation/challenges` - Listar challenges
- `POST /admin/attestation/challenges` - Emitir challenge
- `POST /admin/attestation/challenges/{id}/respond` - Responder challenge
- `GET /admin/attestation/verify` - Status geral
- `GET /admin/attestation/drift` - Drift events
- `GET /admin/attestation/policies` - Listar políticas
- `POST /admin/attestation/policies` - Criar política
- `GET /admin/attestation/measurements` - Medições
- `GET /admin/attestation/measurements/summary` - Sumário medições

### Portal
- `GET /portal/attestation/status` - Status para portal

## Segurança
- Evidence sanitizado (sem secrets/prompts/respostas)
- Imutable audit trail via `immutable_hash` chain
- Replay protection via nonce em challenges
- Tenant isolation via tenant_id nos registros
- Signed evidence placeholder (campo `signed_evidence` com algoritmo configurável)
- Expiração automática de challenges stale
- Revogação explícita de attestations

## Limitações
- **Sem confidential computing real**: TPM/SEV/SGX/VBS são placeholders funcionais
- **Sem conformidade formal**: Não certificado por nenhum órgão
- **Sem hardware real**: Depende de configuração de ambiente
- **Sem SaaS externo**: Toda lógica é local
- **Trust score é heurístico**: Baseado em regras simples, não em ML
- **Evidence não é criptograficamente assinado por hardware real**

## Riscos
- Attestation placeholder pode dar falsa sensação de segurança
- Sem hardware real, trust score é simbólico
- Modo `software_attested` é o padrão e oferece segurança limitada
- Revogação manual não impede acesso se runtime não consulta policy
- Configuração incorreta pode levar a bypass não detectado

## Validação
```bash
pytest tests/test_runtime_attestation.py -v
pytest tests/test_attestation_measurements.py -v
pytest tests/test_attestation_integrity.py -v
pytest tests/test_attestation_governance.py -v
bash scripts/validate-runtime-attestation.sh
```
