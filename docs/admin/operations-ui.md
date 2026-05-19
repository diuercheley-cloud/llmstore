# Interface de Operações (Admin v2)

A nova camada de UX Operacional permite que administradores gerenciem a stack sem a necessidade de ferramentas de linha de comando (CLI) para tarefas cotidianas.

## Visão Geral das Páginas

### 1. Operations Overview
Centraliza as métricas críticas de saúde do sistema, alertas da AIOps e ações de emergência.
- **Status Global**: Indicador em tempo real da saúde da stack.
- **Ações de Emergência**: Botão de pânico para resetar Circuit Breakers e disparar verificações de prontidão.

### 2. Runtime Nodes
Lista todos os nós (workers) de inferência conectados ao Control Plane.
- **Monitoramento**: CPU, Memória e GPU por nó.
- **Drain Mode**: Permite remover um nó do balanceamento de carga de forma segura para manutenção.

### 3. Model Runtime
Gestão do ciclo de vida dos modelos em execução.
- **Redeploy/Rollback**: Controle granular sobre as versões dos modelos nos backends suportados.

### 4. Queue / QoS
Visibilidade sobre as filas de requisição e priorização.
- **Métricas de Fila**: Requisições aguardando por tier de cliente (Admin, Premium, Basic, Free).

### 5. Operational Readiness
Diagnóstico profundo de conectividade e dependências.
- **Checks**: Banco de dados, Redis, Data Plane e permissões de storage.

### 6. Security Posture
Monitoramento de conformidade e riscos.
- **Relatórios**: Geração de relatórios de postura de segurança para auditoria.

## Ações de Operador

- **Reset de Circuit Breaker**: Quando um backend ou modelo entra em falha persistente, o circuito abre. Use esta ação para resetar o estado após corrigir a causa raiz.
- **Node Drain**: Use antes de desligar um servidor ou atualizar o SO de um worker.
- **Readiness Check**: Deve ser executado após qualquer mudança de infraestrutura ou rede.
