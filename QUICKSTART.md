# Quickstart Mode

Quickstart Mode sobe a plataforma inteira com um único container:

```bash
docker run --gpus all \
  -p 8080:8080 \
  ghcr.io/llm-inference-stack/quickstart:latest
```

O container entrega:

- `SQLite`
- perfil operacional `lite`
- modelo local GGUF por padrão (`Gemma 2B`)
- `RAG` local
- Admin UI em `http://localhost:8080/admin-dashboard`

## Primeira inicialização

Na primeira execução o container:

1. inicia `redis-server` embutido;
2. baixa o modelo GGUF caso ele ainda não exista em `/models`;
3. sobe `llama-server` local em `127.0.0.1:8081`;
4. aplica `alembic upgrade head`;
5. faz o seed de backend/modelo/cliente demo;
6. sobe `generation_worker`, `rag_worker` e a API FastAPI.

O healthcheck do container valida:

- `http://127.0.0.1:8081/health`
- `http://127.0.0.1:8080/ready`

## Variáveis úteis

- `HF_TOKEN`: token do Hugging Face, se o repositório do modelo exigir autenticação.
- `MODEL_REPO`: sobrescreve o repositório GGUF.
- `MODEL_FILE`: sobrescreve o arquivo GGUF.
- `MODEL_ID`: id registrado no control plane.
- `ADMIN_TOKEN`: token do Admin UI.
- `JWT_SECRET`: segredo JWT local.

Exemplo com volumes persistentes:

```bash
docker run --gpus all \
  -p 8080:8080 \
  -v llmstack-models:/models \
  -v llmstack-data:/data/quickstart \
  -e HF_TOKEN=hf_xxx \
  ghcr.io/llm-inference-stack/quickstart:latest
```

## Compose mínimo

Também há um compose mínimo em [docker-compose.quickstart.yml](/home/kleber/llm-inference-stack/docker-compose.quickstart.yml).

Uso:

```bash
docker compose -f docker-compose.quickstart.yml up --build
```

## Observações

- O quickstart foi desenhado para GPU NVIDIA porque usa `llama.cpp` com CUDA.
- O default atual é `bartowski/gemma-2-2b-it-GGUF` com `gemma-2-2b-it-Q4_K_M.gguf`.
- O Admin UI usa `ADMIN_TOKEN`. O valor default do container existe só para bootstrap local; troque em qualquer uso persistente.
