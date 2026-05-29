---
owner: platform-ops
status: consolidated
---

# Placeholders de Screenshots

## Propósito

Este diretório contém placeholders sanitizados para screenshots do guia visual de demonstração.

Placeholders são imagens de baixa resolução ou SVG que representam a tela esperada sem conter dados reais ou sensíveis.

## Regras

1. **Nunca commitar screenshots reais** com dados de clientes, tokens ou chaves
2. Placeholders devem ser **SVG ou PNG de baixa resolução** com dados fictícios
3. Nomes de clientes nos placeholders devem usar `demo-` prefix ou valores genéricos
4. Tokens de admin, chaves de API e senhas **nunca** devem aparecer em placeholders

## Formato

```
placeholders/
├── landing-page.svg
├── capabilities.svg
├── admin-dashboard.svg
├── admin-lab.svg
├── client-portal.svg
├── pricing.svg
└── README.md
```

## Geração de Placeholders SVG

Use o script `scripts/prepare-demo-screenshots-local.sh` com a flag `--placeholders-only` para gerar SVGs simples que representam cada tela.

## Validação

```bash
# Verificar se placeholders não contêm secrets
./scripts/validate-demo-visual-guide.sh

# Verificar secrets em todo o repositório
./scripts/check-secrets.sh --all
```
