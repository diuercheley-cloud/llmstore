---
owner: platform-ops
status: consolidated
---

# Troubleshooting

## Docker não sobe

Verifique:

```bash
docker info
docker compose version
```

Se falhar, corrija a instalação do Docker antes de continuar.

## GPU não aparece

Host:

```bash
nvidia-smi
```

Docker:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Se o segundo comando falhar, o runtime NVIDIA do Docker ainda não está funcional.

## Modelo não baixa

Confirme `HF_TOKEN` e o nome do arquivo:

```bash
export HF_TOKEN=seu_token
./scripts/download-model.sh
```

## Stack não fica ready

Inspecione:

```bash
./scripts/test-health.sh
docker compose logs control-plane
docker compose logs data-plane-gemma
docker compose logs postgres
docker compose logs redis
```

## E2E falha

Rode:

```bash
./scripts/validate-e2e.sh
```

Os artefatos ficam em:

```text
artifacts/validation/<timestamp>/
```

## Out of Memory (OOM) na GPU

Se o container `data-plane-gemma` crashar ou reiniciar com erro de CUDA Out of Memory:

1. Reduza `LLAMA_CTX_SIZE` no `.env.local` (ex: 2048 -> 1024).
2. Reduza `LLAMA_N_GPU_LAYERS` (ex: 20 -> 16). Cada layer carregada na GPU consome VRAM.
3. Diminua `LLAMA_BATCH_SIZE`.

Para encontrar o limite da sua placa, use o script de benchmark:
```bash
./scripts/benchmark.sh
```

## Tuning de Performance (RTX 4050/60)

Para GPUs com VRAM limitada (6GB):

- **Flash Attention:** Ative `LLAMA_FLASH_ATTN=true` para reduzir consumo de memória e aumentar velocidade.
- **Layers:** O ideal para o modelo Gemma-4E4B é entre 16 e 24 layers na GPU.
- **Contexto:** 2048 é o padrão equilibrado. 4096 pode causar OOM dependendo das layers.

## Reset local

Se o ambiente estiver inconsistente:

```bash
./scripts/reset-dev.sh
```

Use com cuidado. O script pode remover volumes e opcionalmente `.env` e modelos.
