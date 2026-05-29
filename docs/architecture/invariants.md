---
owner: platform-ops
status: consolidated
---

# Platform Invariants

Este documento define um framework leve de invariants para validacao deterministica e advisory da plataforma.

## Objetivo

- fornecer checks deterministas e testaveis
- manter a plataforma offline-first
- evitar enforcement destrutivo nesta fase
- permitir integracao gradual sem quebrar fluxos existentes

## Estrutura

Os invariants vivem em `app.services.invariants` e retornam `InvariantResult`.

Cada resultado possui:

- `name`
- `passed`
- `severity`
- `message`
- `details`

Todos os resultados atuais usam `severity="advisory"`.

## Invariants Obrigatorios

### Runtime

- every receipt must have `immutable_hash`
- repair operation must emit healing receipt

### Governance

- dry_run must not mutate persistent state

### Trust

- confidential mode must not expose plaintext
- signed artifact must include signature metadata placeholder

### Financial

- tenant-scoped records must include `client_id`

### Sovereign

- exported sovereign bundle must be sanitized

## Regras de Implementacao

- funcoes puras e deterministicas
- sem escrita em banco, disco ou rede
- sem enforcement automatico destrutivo
- foco em validacao e sinalizacao advisory
- compatibilidade com os fluxos atuais

## Validacao

```bash
python3 scripts/validate_invariants.py
make validate-invariants
pytest tests/services/invariants/test_invariants.py
```

