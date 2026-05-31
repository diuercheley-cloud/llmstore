# Real Token Counting System

Este documento descreve o funcionamento e a arquitetura da contagem de tokens real por provider/modelo no control plane.

## Visão Geral

Para substituir estimativas genéricas (como contagem baseada em caracteres ou palavras estáticas) por contabilidade consistente e confiável para faturamento (billing), orçamentos (budgets) e SLOs, foi desenvolvida a infraestrutura de **contagem real de tokens**.

O sistema tenta usar o tokenizer nativo apropriado para o modelo ou provedor requisitado. Caso o tokenizer nativo não esteja disponível (por exemplo, devido a dependências ausentes), o sistema pode recorrer a contagens heurísticas/fallback ou lançar erros dependendo da configuração.

## Arquitetura e Estrutura de Pastas

A infraestrutura reside em `control_plane/app/services/token_counting/`:

- **`token_counter.py`**: O coordenador principal. Avalia o modelo e o provedor para rotear a requisição ao tokenizer correspondente.
- **`openai_token_counter.py`**: Implementa o tokenizer oficial da OpenAI usando a biblioteca `tiktoken` (utilizando a codificação nativa do modelo ou `cl100k_base` como padrão).
- **`anthropic_token_counter.py`**: Tokenizer para Claude usando codificação próxima (`cl100k_base` via `tiktoken`) ou aproximações.
- **`llama_token_counter.py`**: Utiliza a biblioteca `tokenizers` e carrega o arquivo de tokenizer configurado em `TOKENIZER_MODEL_PATH` para modelos locais ou SentencePiece da LLaMA.
- **`fallback_token_counter.py`**: Contador de contingência (fallback) que usa heurística baseada em proporção de palavras/caracteres.

## Feature Flags

O comportamento da contagem de tokens é controlado por duas variáveis de ambiente:

| Variável | Valor Padrão | Descrição |
| :--- | :--- | :--- |
| `TOKEN_COUNTING_REAL_ENABLED` | `true` | Se `true`, ativa a contagem real por tokenizer. Se `false`, o sistema usa apenas a estimativa/fallback heurístico. |
| `TOKEN_COUNTING_FALLBACK_ALLOWED` | `true` | Se `true`, permite o uso do contador de fallback caso ocorram erros ou ausência de dependências (como `tiktoken` não instalado). Se `false`, falha com erro na indisponibilidade do tokenizer real. |

## Integração do Sistema

### 1. Inference Proxy (`InferenceProxy`)
Intercepta requisições síncronas (`_json_forward`) e assíncronas/streaming (`_streaming_forward`).
- **Prompt**: Conta os tokens da mensagem/prompt de entrada antes de fazer a chamada ao data plane.
- **Completion**: Extrai o conteúdo do assistente da resposta recebida e conta os tokens do texto gerado. No caso de streaming, os fragmentos são acumulados e contados após o encerramento do stream.
- **Resposta**: Atualiza o dicionário `usage` na resposta OpenAI retornada para os clientes, inserindo também `tokenizer_used` e `fallback_used`.

### 2. Agent Executor (`AgentExecutor`)
Durante as chamadas de modelo realizadas no ciclo cognitivo do agente, o `AgentLLMProvider` obtém as contagens do `InferenceProxy`.
- Os tokens reais computados incrementam o `run.total_tokens` no banco de dados.
- O custo real estimado do run é atualizado e gravado.

### 3. Billing & Budgets
- **Budgets**: O `AgentBudgetService` valida os limites de custo e tokens por run com base no consumo real contabilizado.
- **Usage & Quotas**: A tabela `usage_records` e `quota_counters` são corrigidos em tempo real para refletir a contagem precisa. No caso de streams, a cota reservada inicialmente (que estima `max_tokens`) é corrigida para o valor real gerado assim que o stream é finalizado.
- **Invoices**: O faturamento mensal e os previews de fatura utilizam os tokens consolidados das tabelas de cotas, eliminando distorções de estimativa.

### 4. Observability (Rastreabilidade)
- Eventos de model call gravam o consumo exato de tokens.
- O tracing gerado pelo `AgentObservabilityService` exporta os tokens reais do run no payload de metadados da span.
