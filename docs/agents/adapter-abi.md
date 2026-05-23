# Agentic Adapter ABI (V1)

Este documento define a Application Binary Interface (ABI) estável para estender as capacidades do LLM Inference Stack sem modificar o código core.

## Visão Geral

O sistema utiliza adapters para desacoplar a lógica de negócio dos provedores de infraestrutura. Existem quatro tipos principais de adapters:

1.  **ToolAdapter**: Permite integrar ferramentas externas (APIs, scripts, bancos de dados).
2.  **MemoryProvider**: Customiza como o histórico e conhecimento do agente são persistidos e recuperados.
3.  **EvalProvider**: Implementa métricas de avaliação customizadas para runs de agentes.
4.  **PlannerProvider**: Permite substituir o motor de planejamento padrão por estratégias alternativas.

## Contrato Base (AdapterABI)

Todos os adapters devem implementar os seguintes métodos:

-   `manifest()`: Retorna metadados (id, versão, compatibilidade, permissões).
-   `schema()`: Define o esquema JSON de configuração e entrada.
-   `healthcheck()`: Verifica se o adapter está operacional (ex: conexão com API externa ativa).
-   `dry_run()`: Valida uma entrada sem executar a ação real.

## Ciclo de Vida do Adapter

1.  **Carregamento**: O Control Plane identifica o adapter via plugin ou SDK.
2.  **Validação de Versão**: O sistema verifica se `compatibility_version` é suportada.
3.  **Verificação de Permissões**: Garante que o adapter possui as permissões necessárias declaradas no manifest.
4.  **Ativação**: Executa `healthcheck()`. Se falhar, o adapter não é disponibilizado para os agentes.
5.  **Execução**: O `AgentExecutor` chama o método `execute()`, `store()`, `retrieve()`, `evaluate()` ou `plan()` conforme o tipo.

## Segurança

-   **Isolamento**: Adapters devem rodar em ambientes controlados (ex: sandbox se forem scripts).
-   **Permissões**: O manifest deve declarar explicitamente quais recursos o adapter acessa.
-   **Sanitização**: O sistema sanitiza automaticamente entradas e saídas seguindo as políticas globais.
