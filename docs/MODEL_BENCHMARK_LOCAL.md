---
owner: platform-ops
status: consolidated
---

# Benchmark de Modelos Locais

Este documento descreve como utilizar os scripts de benchmark para avaliar a performance de modelos rodando localmente (ex: via llama.cpp ou LM Studio).

## Objetivo

O objetivo principal é medir métricas essenciais como:
- Tokens por segundo
- Latência total
- Time to First Token (TTFT)
- Uso de VRAM

Com base nesses resultados, o sistema recomenda em quais planos (free, basic, premium) um modelo pode ser disponibilizado sem degradar a experiência do usuário.

## Como Executar

### Modos Disponíveis

- `--quick`: Roda 1 única requisição curta (20 tokens). Ideal para sanidade.
- `--standard`: Roda 3 requisições (100 tokens cada). Modo padrão recomendado.
- `--stress`: Modo de carga pesada. Exige confirmação manual. Roda 10 requisições com concorrência 5 e 256 tokens cada.

### Argumentos Principais

- `--model`: Nome do modelo (obrigatório).
- `--streaming`: `true` ou `false` (padrão `false`).
- `--output-dir`: Onde salvar os resultados (padrão `artifacts/model-benchmarks`).
- `--prompt-file`: Caminho para um arquivo com o prompt a ser usado.

## Métricas Coletadas

Além das métricas básicas, o novo runner coleta:
- **TTFT P95**: Time to First Token no percentil 95.
- **Latência P95**: Latência total no percentil 95.
- **Taxa de Erro**: Percentual de falhas e timeouts.
- **Métricas de Sistema**: Carga de CPU, memória RAM usada e uso de VRAM (via nvidia-smi).
- **Dados do Backend**: ID do backend, tipo (llama-cpp, vllm, etc) e se houve fallback.

## Recomendações de Plano

O script analisa os resultados e sugere uma categoria:
- `safe_for_free`: Alta vazão (>30 tps) e baixa latência.
- `safe_for_basic`: Vazão moderada (>15 tps).
- `safe_for_premium`: Baixa vazão ou alta latência, recomendado para uso dedicado.
- `not_recommended`: Alta taxa de erro ou performance abaixo do aceitável.

## Validação Real

Para validar o pipeline completo de benchmark real:
```bash
make validate-benchmark-real
```
