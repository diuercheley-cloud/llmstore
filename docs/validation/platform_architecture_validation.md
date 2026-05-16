# Platform Architecture Validation

Este documento descreve a suite unificada de validacao arquitetural da plataforma.

## Objetivo

- agregar validacoes arquiteturais em um comando unico
- funcionar offline
- nao depender de servicos externos
- produzir uma saida clara para operadores e desenvolvimento

## Comando

```bash
make validate-platform-architecture
```

Ou diretamente:

```bash
python3 scripts/validate_platform_architecture.py
```

## Validacoes Executadas

Quando disponiveis, a suite executa:

- `scripts/validate_architecture_boundaries.py`
- `scripts/validate_runtime_contracts.py`
- `scripts/validate_domain_contracts.py`
- `scripts/validate_adrs.py`
- `scripts/validate_invariants.py`

## Comportamento

- retorna `0` quando todas as validacoes executadas passam
- retorna `1` quando qualquer validacao executada falha
- marca validadores ausentes como `SKIP`
- usa apenas scripts locais do repositorio

## Saida

A saida mostra:

- nome da suite
- repositorio alvo
- modo de execucao offline-only
- status por validador: `PASS`, `FAIL` ou `SKIP`
- `exit_code` por validador
- resumo da saida de cada script

## Escopo

Esta suite cobre verificacoes de arquitetura documental e contratual. Ela nao substitui suites funcionais, e2e, de banco ou de infraestrutura.

