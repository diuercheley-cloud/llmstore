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

Utilize o script principal ou os comandos do `Makefile`:

```bash
# Via Makefile (roda um teste rapido usando configuracoes padrao)
make benchmark-model

# Via Script diretamente
./scripts/benchmark-model-local.sh --model "gemma-2b" --runs 5 --concurrency 2
```

### Argumentos Principais

- `--model`: Nome do modelo (obrigatório).
- `--tokens`: Número de tokens a gerar (padrão 50).
- `--runs`: Número de vezes que o teste rodará (padrão 3).
- `--concurrency`: Requisições concorrentes (padrão 1).
- `--streaming`: `true` ou `false` (padrão `false`).
- `--quick`: Roda um teste extremamente rápido para validar configurações.

## Relatórios

Os resultados são salvos em `artifacts/model-benchmarks/<model>/<timestamp>/` e incluem:
- `benchmark.json`: Métricas estruturadas.
- `benchmark.md`: Resumo legível com recomendações.
- `raw-results.jsonl`: Respostas e timings brutos.

## Validação

Para validar se o pipeline de benchmark está funcionando, rode:
```bash
./scripts/validate-benchmark-local.sh
```
Isso validará o formato dos JSONs e testará cenários de erro.
