---
owner: platform-ops
status: consolidated
---

# Domain Contracts

Este documento define contratos minimos para os dominios candidatos a modularizacao forte em `app.domains`.

## Objetivo

- preparar a plataforma para extracao futura de modulos sem mover codigo existente agora
- preservar imports existentes baseados em `app.*`
- evitar dependencia obrigatoria entre dominios
- manter a arquitetura offline-first

## Estrutura

Cada dominio possui:

- `__init__.py`
- `README.md`
- `contracts.py`
- `events.py`
- `exceptions.py`

Os contratos sao classes Python simples, declarativas e sem logica pesada. Cada classe documenta:

- `allowed_inputs`
- `emitted_events`
- `forbidden_dependencies`
- `deterministic_requirements`

## Relacao com Platform Core Contracts

Os dominios definidos aqui utilizam os **Platform Core Contracts** (veja [platform-core-contracts.md](platform-core-contracts.md)) para garantir interfaces estritas e testaveis entre componentes core como providers, plugins, routing e attestation.

## Dominios

### Runtime

Responsavel pela superficie de execucao, roteamento, providers e fluxos deterministas de runtime.

### Governance

Responsavel por politicas, aprovacoes, enforcement e trilhas de auditoria regulatoria.

### Trust

Responsavel por receipts, verificacao criptografica, atestacao e integridade.

### Financial

Responsavel por faturamento, conciliacao, anomalias e trilhas financeiras.

### Sovereign

Responsavel por operacao air-gapped, mesh soberano, replicacao local e appliance soberano.

### Operations

Responsavel por observabilidade, onboarding, operacao administrativa e exportacao de relatorios.

## Regras Arquiteturais

- os contratos nao devem mover nem reescrever implementacoes existentes
- imports legados devem continuar funcionando
- contratos de um dominio nao devem importar contratos de outro dominio
- os contratos devem continuar utilizaveis em ambiente local sem dependencia obrigatoria de servicos online
- `forbidden_dependencies` funciona como documentacao executavel para a modularizacao futura

## Validacao

Use:

```bash
python3 scripts/validators/validate_domain_contracts.py
make validate-domain-contracts
pytest tests/integration/domains/test_domain_contracts.py
```

