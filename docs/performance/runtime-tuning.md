# Runtime Tuning & Performance Dashboard

A nova camada de Performance Tuning permite monitorar, analisar e otimizar o comportamento da stack em tempo real.

## Conceitos Chave

### 1. Benchmarking
O sistema permite disparar benchmarks sintéticos para medir a capacidade real de um modelo em um determinado hardware/configuração.
- **Métricas Coletadas**: TPS (Tokens per second), Latência (p50, p95, p99), Pressão de GPU, Cache Hit Ratio e Erros.
- **Histórico**: Todos os resultados são persistidos para comparação temporal (Antes/Depois).

### 2. Perfis de Tuning
Estratégias pré-configuradas que podem ser aplicadas com um clique:
- **Balanced**: Otimização padrão para uso geral.
- **Low Latency**: Prioriza o tempo de resposta, ideal para chatbots e interfaces interativas.
- **High Throughput**: Prioriza o volume total de tokens, ideal para processamento em lote.
- **Low Cost**: Prioriza modelos locais e caches agressivos para reduzir custos de nuvem.

### 3. Engine de Recomendação (AIOps)
Baseado nos resultados do benchmark, o sistema sugere mudanças específicas:
- **Fila Alta**: Sugere aumentar paralelismo.
- **GPU Perto do Limite**: Sugere reduzir contexto ou batch size.
- **Cache Hit Baixo**: Sugere ativar cache semântico.

## Segurança e Operação

### Modo Advisory (Padrão)
Por padrão, o tuning opera em modo **Advisory**. Isso significa que as recomendações são visíveis e os eventos de aplicação de perfil são logados, mas as configurações reais do ambiente (env vars) não são alteradas automaticamente.

### Modo Enforcement
Para permitir que o sistema aplique as configurações reais, defina:
`RUNTIME_TUNING_APPLY_ENABLED=true`

### Auditoria e Rollback
Cada mudança de perfil gera um `RuntimeTuningEvent` que registra:
- Quem aplicou.
- Qual era a configuração anterior.
- Qual é a nova configuração.
- Se foi uma ação real ou apenas advisory.
