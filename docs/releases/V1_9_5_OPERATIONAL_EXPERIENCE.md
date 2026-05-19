# Release v1.9.5 - Operational Experience

Esta release transforma o `llm-inference-stack` em uma plataforma operacional madura, focada na redução de atrito para operadores e na excelência em deployments enterprise.

## Pilares da Release

### 1. Automação e Deployment
- **Preflight Checks**: Garantia de ambiente antes da instalação.
- **Appliance Automation**: Deployment local reprodutível e seguro.
* **Kubernetes Ready**: Suporte a Helm com separação clara de segredos.

### 2. Tuning e Performance
- **AIOps Recommendations**: Sugestões automáticas baseadas em benchmarks.
- **Profiles**: Estratégias de baixo custo, baixa latência ou alto throughput.

### 3. Observabilidade e SLO
- **Dashboards Grafana**: Visualização completa de GPU, nós e filas.
- **Error Budgets**: Monitoramento rigoroso da disponibilidade.

### 4. Enterprise Onboarding
- **Handover Packs**: Documentação técnica automatizada para clientes.
- **Project Tracking**: Checklist completo de ativação.

### 5. Multi-Cluster
- **Global Control**: Operação de múltiplos clusters a partir de um único painel.
- **Sovereignty**: Segurança rigorosa no transporte de metadados cross-cluster.

## Breaking Changes
- Nenhuma. Todas as novas features são opt-in e não afetam o funcionamento single-cluster atual.

## Como Atualizar
```bash
make upgrade-release
```
