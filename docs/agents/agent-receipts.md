# Agent Execution Receipts

Os recibos de execução (`AgentRunReceipt`) são artefatos de auditoria gerados para cada execução de ferramenta bem-sucedida ou falha no runtime de agentes.

## Estrutura do Recibo

Cada recibo contém:
- **run_id**: Vínculo com a execução mestre.
- **step_number**: O passo exato em que a ferramenta foi invocada.
- **signature**: Uma assinatura digital/hash que valida a autenticidade do recibo gerado pelo Control Plane.
- **receipt_data**:
  - `input_hash`: SHA-256 dos parâmetros de entrada.
  - `output_hash`: SHA-256 do resultado retornado pela ferramenta.
  - `success`: Booleano indicando se a execução foi concluída.
  - `failure_reason`: Detalhes em caso de erro.
  - `timestamp`: Momento exato da geração.

## Finalidade

1. **Compliance**: Prova irrefutável de que uma ação foi tomada ou tentada.
2. **Depuração**: Permite validar se o output de uma ferramenta mudou para os mesmos inputs em cenários de replay.
3. **Billing**: Pode ser usado como base para faturamento de uso de ferramentas de terceiros ou sandboxes pagas.
