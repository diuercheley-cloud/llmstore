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

## Riscos
- Quebra de integrações legadas.
- Perda de funcionalidades específicas não migradas.
- Confusão durante a transição.
