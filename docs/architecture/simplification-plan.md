---
owner: platform-ops
status: consolidated
---

# Plano de Simplificação de Arquitetura

Este documento descreve a estratégia para reduzir a duplicação e complexidade no `llm-inference-stack`.

## Visão Geral
A plataforma acumulou múltiplas versões de funcionalidades administrativas, modelos de dados e documentação. Este plano visa consolidar essas áreas em um padrão único e moderno.

## Estratégia por Área

### 1. Endpoints de API
- **Manter**: `commercial_*_admin.py`, `observability_admin.py`, `saas_admin.py`.
- **Depreciar**: `admin.py` (legado), `admin_models_runtime.py`, `billing_admin.py`.
- **Migrar**: Funcionalidades de `admin.py` para routers específicos e modulares.

### 2. Serviços
- **Manter**: `model_runtime_manager.py`, `platform_slo.py`.
- **Depreciar**: `admin_model_management.py` (substituído por serviços especializados).
- **Consolidar**: `billing/` e `payment_adapters/` em um módulo unificado de faturamento.

### 3. Documentação
- **Manter**: `docs/*` organizado por categorias.
- **Remover**: `SECURITY_LOCAL.md` (consolidado em `docs/security/`), `INSTALL.md` (substituído por `docs/INSTALL.md` ou similar).

### 4. Scripts
- **Padronizar**: Usar `scripts/` como local único.
- **Depreciar**: Scripts na raiz do repositório (ex: `list_backends.py`).

## Plano de Compatibilidade
1. Adicionar header `X-Deprecated-Endpoint` em rotas legadas.
2. Emitir warnings nos logs ao utilizar serviços depreciados.
3. Atualizar documentação com avisos de depreciação e links para os novos padrões.

## Orçamentos de Manutenção

Novas expansões de superfície e dívida crítica são bloqueadas pelos orçamentos em
`config/maintenance-budgets.json`. Sempre que routers, serviços, flags ou serviços
P0/P1 sem testes forem removidos, o orçamento correspondente deve ser reduzido.

O freeze legado por allowlist permanece apenas como verificação de governança:
suas listas históricas não representam toda a superfície atual. Ativá-lo sem
reconciliação bloquearia componentes existentes. Os budgets são o controle
obrigatório contra crescimento até essa reconciliação ser concluída.

## Controles de Risco

- Quebra de integrações legadas: preservar rotas públicas e exigir rollback story
  na classificação de superfície suportada.
- Perda de funcionalidades específicas: executar coleta integral e suítes de
  contratos, qualidade e segurança antes de remover uma superfície.
- Confusão durante a transição: manter versão única em `VERSION`, documentação e
  artefatos de release.
- Crescimento arquitetural: bloquear regressões pelos budgets não crescentes.
- Dívida de testes crítica: impedir aumento de serviços P0/P1 sem cobertura e
  reduzir seus limites sempre que cobertura for adicionada.
- Falhas silenciosas de Python: bloquear nomes indefinidos, redefinições e
  `except` vazio no lint funcional.
