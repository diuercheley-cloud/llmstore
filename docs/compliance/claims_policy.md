# Claims Policy

Este documento define o guardrail de documentacao contra claims proibidas sobre seguranca, certificacao e attestation.

## Objetivo

- evitar promessas indevidas em documentacao, scripts e ativos estaticos
- impedir claims que excedam a implementacao real do projeto
- permitir explicacoes honestas sobre limites, placeholders e ausencia de certificacao

## Claims Proibidas

As seguintes frases nao devem aparecer como claim positiva do produto:

- `military-grade`
- `unbreakable`
- `formally certified`
- `guaranteed secure`
- `real hardware attestation`
- `government certified`
- `certified SOC2`
- `certified FedRAMP`
- `certified confidential computing`

## Contextos Permitidos

O guardrail permite essas frases apenas quando o texto deixa claro que o projeto:

- `does not claim` essas propriedades
- `does not provide` essas garantias
- usa `placeholder` ou `placeholder_attestation`
- esta `not certified`
- documenta explicitamente `limitations`

## Escopo

O validador escaneia:

- `docs/`
- `README.md`
- `app/static/` quando existir
- `control_plane/app/static/` no layout atual do repositorio
- `scripts/`

## Notas

- O guardrail nao bloqueia referencias a `SOC2-style controls`.
- O guardrail nao bloqueia `placeholder_attestation`.
- O guardrail nao bloqueia documentacao que explique limitacoes e ausencia de certificacao.

## Validacao

```bash
python3 scripts/validate_claims.py
make validate-claims
```

