---
owner: platform-ops
status: consolidated
---

# GPU Orchestration

O LLM Inference Stack gerencia de forma inteligente os recursos de GPU para otimizar a alocação de modelos e garantir alta disponibilidade.

## Coleta de Métricas

O serviço `GpuOrchestrator` utiliza o utilitário `nvidia-smi` para coletar dados em tempo real sobre:
- Utilização da GPU (%)
- Uso de memória de vídeo (VRAM)
- Temperatura
- Processos ativos

## Alocação de Modelos

Ao carregar um novo modelo, o orquestrador verifica a memória disponível em cada GPU do nó e seleciona a mais adequada (geralmente a com menor carga).

## Pressão de Memória

Se a utilização da memória GPU ultrapassar limites críticos, o orquestrador pode emitir alertas ou impedir novas alocações no nó afetado.
