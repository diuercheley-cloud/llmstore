# Multi-Cluster Operations

O `llm-inference-stack` suporta a operação de múltiplos clusters ou appliances de forma unificada através do Control Plane.

## Tipos de Cluster

- **Primary**: O cluster principal que recebe a maioria do tráfego.
- **Standby**: Cluster de reserva pronto para assumir em caso de falha (Warm Standby).
- **Edge**: Clusters menores localizados próximos aos usuários para redução de latência.
- **Isolated / Airgap**: Clusters sem conexão externa constante, operando em redes segregadas.

## Operações de Tráfego

### 1. Drenagem (Drain)
A operação de drain marca o cluster para não receber novas requisições, permitindo que as requisições em andamento terminem de forma limpa antes de uma manutenção.

### 2. Modo de Manutenção
Coloca o cluster em um estado de pausa total. Nenhuma requisição será enviada para este cluster pelo roteador global.

### 3. Promoção de Standby
Transforma um cluster Standby em Primary. Esta é uma operação crítica que exige auditoria obrigatória.

## Segurança e Sincronização

A sincronização entre clusters é projetada com foco em segurança:
- **Status-only**: Por padrão, apenas metadados de status e saúde são sincronizados.
- **Data Boundaries**: Prompts de usuários e documentos de RAG **nunca** são sincronizados entre clusters por padrão.
- **Auto-Failover**: O failover automático é desativado por padrão. Deve ser ativado via:
  `MULTI_CLUSTER_AUTO_FAILOVER_ENABLED=true`
