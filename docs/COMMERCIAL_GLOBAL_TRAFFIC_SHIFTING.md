# Commercial Global Traffic Shifting (Phase 17)

## Objetivo

Permitir o *shifting* gradual de tráfego real entre clusters de inferência usando roteamento baseado em pesos (*weighted routing*), controlado por administradores e sob rigorosas restrições de segurança e health-checks.

## Diferença entre Global Router (Phase 16) e Traffic Shifting (Phase 17)

- **Phase 16 (Global Router)**: Introduziu a capacidade analítica (em dry-run) de recomendar o melhor cluster globalmente baseado em margem, latência e custo. Nenhuma requisição é efetivamente enviada via proxy na rede.
- **Phase 17 (Traffic Shifting)**: Introduz a capacidade de definir *policies* administrativas explícitas para mover % do tráfego (canary/dry_run). Prepara o terreno para forwarding real cross-cluster na Phase 18, atuando como o plano de controle que distribui as requisições baseando-se em % e buckets determinísticos.

## Funcionalidades e Mecanismos

### 1. Weighted Routing & Deterministic Bucket
Para evitar *flapping* (onde a mesma conversa/cliente oscila entre clusters diferentes, causando miss de cache de contexto), o routing usa um `deterministic_bucket` entre 1 e 100 baseado em:
`hash(correlation_id OR request_id OR client_id) % 100`
Se a policy define 5% de tráfego, buckets 1 a 5 sofrerão *shift*.

### 2. Modes (Dry Run vs Canary)
Por padrão, a feature é iniciada em `dry_run`.
- **Dry Run**: O tráfego não muda de cluster (stay_local), mas o sistema audita "dry_run_would_shift" para validação em dashboards.
- **Canary**: O tráfego seria de fato encaminhado para o cluster remoto (`shift_to_target`). O limite padrão (`COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MAX_CANARY_PERCENT`) garante que nunca passe de ex: 10% sem aprovação prévia.

### 3. Automatic Rollback & Health Checks
O sistema jamais fará routing para um target offline. O `check_cluster_health` deve aprovar o status. Se métricas distribuídas reportarem `error_rate` alto, `auto_rollback_unhealthy_policies` pausará a policy para evitar downtime generalizado.

### 4. Limitações Atuais (Preparação para Fase 18)
Na Fase 17, as decisões são calculadas, persistidas e expostas em metadata, porém o proxy HTTP Cross-Cluster real e seguro via TLS mútuo / JWT tokens ainda não interliga os fluxos de rede (Isso é feito na Fase 18). Ou seja, neste exato momento, o tráfego não navega fisicamente para outro cluster na camada HTTP, preservando OpenAI-compatibility local, servindo de fundação robusta.
