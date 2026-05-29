---
owner: platform-ops
status: consolidated
---

# Saúde da Plataforma

Este documento descreve como o status de saúde da plataforma é calculado e interpretado.

## Endpoint de Saúde
`GET /admin/observability/platform-health`

## Níveis de Saúde
- **OK**: Todos os SLOs críticos estão sendo atendidos e não há falhas sistêmicas detectadas.
- **WARNING**: Algum SLO não crítico está fora da meta, ou falhas isoladas (como attestation ou hot-swap) foram detectadas recentemente.
- **CRITICAL**: SLOs críticos (Availability) estão abaixo do limite ou há falhas sistêmicas impactando múltiplos usuários.

## Indicadores de Saúde Sistêmica

### 1. Integridade de Hardware (Attestation)
Falhas de `llm_attestation_failures_total` indicam que nós de computação podem estar comprometidos ou com falha física.

### 2. Estabilidade de Runtime
`llm_model_hot_swap_failures_total` indica problemas ao carregar novos modelos na GPU, o que pode levar a indisponibilidade de modelos específicos.

### 3. Segurança (RBAC)
Picos em `llm_rbac_denials_total` podem indicar tentativas de ataque ou desconfiguração massiva de permissões.

### 4. Pressão de Recursos
`llm_gpu_memory_pressure_ratio` acima de 0.9 indica que a plataforma está próxima da saturação, o que impactará a latência e aumentará as filas.
