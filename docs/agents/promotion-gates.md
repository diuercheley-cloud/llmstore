# Agent Promotion Gates

O `llm-inference-stack` utiliza um processo rigoroso de **Promotion Gates** para garantir que agentes, adapters e prompts só cheguem ao ambiente de produção após validação técnica, de segurança e de conformidade.

## Critérios do Gate de Promoção

Para que um agente seja promovido (ex: de `draft` para `active`), ele deve obrigatoriamente passar pelos seguintes checks:

1.  **Eval Baseline Passed**: O agente deve possuir um baseline de avaliação (`AgentEvalBaseline`) com métricas que atendam aos requisitos mínimos (ex: `score >= 0.8`).
2.  **Security Check Passed**: Validação contra injeção de prompts, vazamento de segredos e acesso a ferramentas não autorizadas.
3.  **Compatibility Check**: Verificação de que o agente é compatível com a versão atual do Control Plane e do Data Plane.
4.  **Prompt Freshness**: O prompt atual deve corresponder exatamente ao hash registrado no último baseline aprovado (`AgentPromptBaseline`). Qualquer alteração no prompt exige um novo ciclo de evals.
5.  **No Critical Incidents**: Não podem existir incidentes de severidade `critical` abertos para o agente.
6.  **Owner Approval**: A promoção deve ser solicitada ou aprovada pelo proprietário (`owner`) designado.

## Ciclo de Vida de Promoção

### 1. Verificação (`promotion-check`)
O administrador solicita um check preventivo. O sistema avalia todos os critérios e retorna um relatório detalhado de sucessos e bloqueios.

### 2. Baseline de Prompt
Toda vez que um agente é promovido, o estado do seu prompt (instruções e versão do modelo) é "congelado" em um `AgentPromptBaseline`. Se o desenvolvedor alterar o prompt, o gate de promoção bloqueará a entrada em produção até que um novo baseline seja gerado via evals.

### 3. Promoção Real (`promote`)
Se todos os checks do gate passarem, o status do agente é atualizado e um evento `agent_promoted` é registrado na timeline do sistema para auditoria.

## APIs Administrativas

- **POST** `/admin/agents/governance/{id}/promotion-check`: Executa a bateria de testes sem alterar o status.
- **POST** `/admin/agents/governance/{id}/promote`: Executa os testes e, se aprovado, promove o agente.
- **GET** `/admin/agents/governance/{id}/promotion-history`: Lista o histórico de tentativas e sucessos de promoção.

## Rollback Plan

Toda promoção deve ser acompanhada de um plano de rollback automático ou manual, permitindo retornar ao status anterior em caso de degradação de performance detectada pós-promoção.
