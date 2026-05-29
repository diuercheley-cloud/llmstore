---
owner: platform-ops
status: consolidated
---

# Compensation Logic

Ações de compensação são usadas para desfazer ou mitigar os efeitos de tarefas que falharam em um fluxo complexo (padrão Saga).

## Como Funciona

1. Ao definir uma tarefa, uma `compensation_action` pode ser registrada.
2. Se a tarefa falhar e não puder ser recuperada por retentativas, o Task Engine aciona o `CompensationService`.
3. O serviço executa a lógica de reversão (ex: deletar um arquivo criado, estornar uma transação).

## Exemplo de Saga

1. Tarefa A: Criar usuário (Compensação: Deletar usuário).
2. Tarefa B: Alocar recurso (Compensação: Liberar recurso).
3. Tarefa C: Enviar e-mail (Sem compensação fácil - ação final).

Se a Tarefa B falhar, a Tarefa A é compensada para manter a consistência do sistema.
