# Proposta Técnica — Local AI Appliance

> **Atenção:** Este documento é um template. Substitua `[Nome do Cliente]`, `[Data]` e demais placeholders antes de entregar ao cliente.
> Esta proposta descreve um **appliance local**. Não oferecemos cloud gerenciada.
> Billing é local/manual — não inclui PSP/PIX real.

---

**Cliente:** [Nome do Cliente]
**Data:** [Data]
**Versão:** 1.0
**Responsável:** [Nome do Responsável]

---

## 1. Visão Geral

O Local AI Appliance é uma plataforma local de LLM-as-a-Service que expõe API 100% compatível com OpenAI, com suporte nativo a RAG (Retrieval-Augmented Generation), TTS (Text-to-Speech), billing local/manual, portal do cliente e painel administrativo. Tudo roda **on-premise**, na infraestrutura do cliente.

### Objetivo

Prover capacidade de IA generativa com controle total sobre dados, custos previsíveis e integração imediata com ecossistemas existentes (LangChain, Open WebUI, n8n, OpenAI SDK).

---

## 2. Arquitetura

```
                            +-----------------------+
                            |    Clientes Externos   |
                            | (Aplicações, SDKs, UI) |
                            +-----------+-----------+
                                        |
                                        v
+------------------------------------------------------------------+
|                     Control Plane (FastAPI)                       |
|  - Autenticação (API Keys hasheadas)                             |
|  - Rate limiting (Redis)                                         |
|  - Quotas e auditoria (PostgreSQL)                               |
|  - Roteamento OpenAI-compatible                                  |
|  - Fila, timeout, circuit breaker                                |
|  - Admin API + Dashboard                                         |
|  - Client Portal                                                 |
|  - Billing local/manual                                          |
|  - RAG engine                                                    |
|  - TTS proxy                                                     |
+------------------------------------------------------------------+
          |                        |                    |
          v                        v                    v
+-------------------+   +-------------------+   +------------------+
|  Data Plane       |   |  PostgreSQL       |   |  Redis           |
|  (llama.cpp)      |   |  (Clientes, uso,  |   |  (Rate limit,    |
|  Inferência Local |   |   faturas, logs)  |   |   cache, fila)   |
|  GPU/CPU          |   |   Local           |   |   Local          |
+-------------------+   +-------------------+   +------------------+
```

### Separação de Responsabilidades

- **Control Plane:** Autenticação, autorização, clientes, API keys, quotas, rate limit, logs, métricas, health, ready, histórico, modelos, fila, billing e RAG.
- **Data Plane:** Apenas inferência do modelo. Não exposto para clientes externos.
- **PostgreSQL:** Persistência de clientes, uso, faturas, logs de requisição.
- **Redis:** Rate limiting, fila, cache de respostas.

---

## 3. Componentes

| Componente | Tecnologia | Função |
|------------|-----------|--------|
| Control Plane | Python / FastAPI | API REST, autenticação, orquestração |
| Data Plane | llama.cpp | Inferência do modelo GGUF |
| Banco de Dados | PostgreSQL 16 | Persistência de dados |
| Cache/Fila | Redis 7 | Rate limiting, fila, cache |
| Modelo | GGUF (Gemma 4, Llama 3, Mistral, etc.) | Modelo de linguagem |
| TTS | pocket-tts | Síntese de voz local |
| Proxy | Caddy (modo produção) | TLS, reverse proxy |
| Monitoria | Prometheus + Grafana (opcional) | Métricas e dashboards |

---

## 4. Requisitos de Hardware

### Mínimo (CPU-only, testes)

| Componente | Especificação |
|------------|---------------|
| CPU | 8 cores x86_64 |
| RAM | 16 GB |
| Armazenamento | 100 GB SSD |
| Rede | 1 Gbps |

### Recomendado (Produção com GPU)

| Componente | Especificação |
|------------|---------------|
| CPU | 8+ cores x86_64 |
| RAM | 32 GB |
| GPU | NVIDIA RTX 3060+ (12 GB VRAM mínimo recomendado) |
| Armazenamento | 500 GB SSD NVMe |
| Rede | 1 Gbps |

### Enterprise (Alta disponibilidade)

| Componente | Especificação |
|------------|---------------|
| CPU | 16+ cores x86_64 |
| RAM | 64+ GB |
| GPU | NVIDIA RTX 4090 / A4000+ (24+ GB VRAM) |
| Armazenamento | 1 TB SSD NVMe (RAID 1 opcional) |
| Rede | 10 Gbps |

**Observações:**
- GPU NVIDIA com suporte CUDA 12+ é fortemente recomendada para produção.
- O sistema funciona em CPU, mas com throughput significativamente menor.
- WSL2 no Windows suporta GPU NVIDIA via Docker.
- Apple Silicon (MPS) não é suportado nativamente.

---

## 5. Requisitos de Software

| Software | Versão Mínima | Observação |
|----------|--------------|------------|
| Docker | 24+ | Engine e Compose V2 |
| NVIDIA Driver | 545+ | Apenas se usar GPU |
| NVIDIA Container Toolkit | 1.14+ | Apenas se usar GPU |
| Sistema Operacional | Linux (Ubuntu 22.04+/Debian 12+) ou Windows com WSL2 | |

---

## 6. Segurança

### Controles Implementados

- **API keys armazenadas com hash bcrypt.** A chave original é exibida apenas uma vez no momento da criação.
- **Isolamento multi-tenant.** Cada cliente possui índice RAG, cotas e chaves próprias.
- **Rate limiting por cliente.** Sliding window via Redis. Cliente que excede recebe HTTP 429.
- **Bloqueio automático.** Cliente suspenso por inadimplência ou violação de cota.
- **Sem telemetria externa.** Nenhum dado é enviado para servidores externos por padrão.
- **CORS configurável.** Restrito ao domínio do appliance em modo produção.
- **Relatórios de segurança.** Script `scripts/validators/security-report-local.sh` varre secrets, permissões e exposição.

### Observações Importantes

- **Não garantimos segurança absoluta.** Recomendamos avaliação pelo time de segurança do cliente.
- **Não substituímos firewall, WAF ou outras camadas de rede.**
- **Não substituímos análise de compliance.** O cliente deve avaliar adequação à LGPD e demais regulamentações.

---

## 7. Operação Local

- Toda inferência, armazenamento e indexação RAG ocorrem **exclusivamente dentro da rede do cliente**.
- O sistema opera **100% air-gapped** após instalação e download do modelo.
- Nenhum prompt, resposta, documento ou metadado é enviado para servidores externos.
- Não há dependência de APIs cloud para funcionamento básico.

---

## 8. Backups

O sistema inclui scripts de backup e restore:

```bash
# Realizar backup
./scripts/backup/backup.sh

# Restaurar
./scripts/backup/restore.sh /caminho/para/postgres.dump
```

O backup inclui:
- Dump completo do PostgreSQL (clientes, uso, faturas, logs)
- Estrutura de diretórios e configurações

**Recomendações:**
- Backup diário automatizado via cron
- Armazenamento em local separado do servidor de produção
- Teste de restore periódico (recomendado trimestralmente)

---

## 9. Upgrade / Rollback

### Processo de Upgrade

Documentação detalhada em `docs/UPGRADE_ROLLBACK_LOCAL.md`.

1. Realizar backup completo
2. Baixar nova versão do repositório
3. Executar `./scripts/deploy/upgrade-local.sh`
4. Validar com `./scripts/validators/validate-e2e.sh`

### Rollback

- Restaurar backup anterior via `./scripts/backup/restore.sh`
- Reverter versão do repositório
- Subir stack novamente

---

## 10. RAG (Retrieval-Augmented Generation)

### Capacidades

- Indexação de documentos nos formatos TXT, PDF e Markdown
- Índice isolado por cliente (cliente A não acessa documentos do cliente B)
- Busca por similaridade semântica (top_k configurável)
- Resposta gerada pelo modelo com base no contexto recuperado

### API

```bash
POST /v1/rag/query
Authorization: Bearer {API_KEY}
Content-Type: application/json

{
  "question": "Pergunta do usuário",
  "top_k": 3
}
```

### Scripts de Validação

- `./scripts/validators/validate-rag-local-multiclient.sh` — valida isolamento entre clientes
- `./scripts/legacy/clean-rag-local-data.sh` — limpa dados de RAG

---

## 11. TTS (Text-to-Speech)

### Capacidades

- Síntese de voz 100% local via pocket-tts
- Sem dependência de APIs cloud (Google Cloud TTS, Azure Speech, etc.)
- Útil para call centers, IVR, acessibilidade

### API

```bash
POST /pocket-tts/tts
Authorization: Bearer {API_KEY}
Content-Type: application/json

{
  "text": "Texto para converter em áudio"
}
```

### Status

Endpoint `GET /pocket-tts/health` para verificar disponibilidade do serviço.

---

## 12. Compatibilidade OpenAI

A API é **100% compatível com o formato OpenAI**, permitindo drop-in replacement.

### Endpoints Suportados

| Endpoint | OpenAI Equivalente |
|----------|-------------------|
| `GET /v1/models` | Lista modelos disponíveis |
| `POST /v1/chat/completions` | Chat completion (streaming e não-streaming) |
| `POST /v1/embeddings` | Geração de embeddings |
| `POST /v1/responses` | Responses API (beta) |

### Exemplo de Uso

**Python (OpenAI SDK):**
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:18080/v1",
    api_key="sk-demo-xxxx"
)

response = client.chat.completions.create(
    model="unsloth/gemma-4-E4B-it-GGUF",
    messages=[{"role": "user", "content": "Hello"}]
)
```

**LangChain:**
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:18080/v1",
    api_key="sk-demo-xxxx",
    model="unsloth/gemma-4-E4B-it-GGUF"
)
```

**Ferramentas compatíveis:** LangChain, LlamaIndex, Open WebUI, n8n, AnythingLLM, Flowise.

---

## 13. Limitações

### Modelos

- Modelos locais (GGUF) têm capacidade inferior a modelos cloud como GPT-4, Gemini Ultra ou Claude Opus em tarefas de raciocínio complexo e conhecimento enciclopédico.
- Para 80% dos casos de uso empresariais (suporte, análise de documentos, RAG, assistentes internos), o desempenho é equivalente.

### Escala

- Escala vertical (GPU mais potente) é o caminho recomendado.
- Escala horizontal (múltiplos data planes) é possível mas requer configuração adicional.
- Não oferecemos cloud gerenciada ou cluster automático.

### Billing

- Billing é local/manual. **Não inclui PSP/PIX real.**
- Faturamento requer confirmação manual do administrador.
- Sem automação de cobrança (boletos automáticos, PIX, cartão).

### Disponibilidade

- Não há HA (High Availability) nativo. Recomendamos redundância de hardware para missão crítica.
- SLA depende do contrato de suporte contratado.

---

## 14. Escopo Excluído

O que **não está incluído** nesta proposta:

- ☐ Cloud gerenciada / SaaS multi-tenant
- ☐ Integração PSP/PIX real
- ☐ Fine-tuning de modelos (apenas RAG e inferência)
- ☐ Infraestrutura de rede (firewall, load balancer)
- ☐ Hardware (servidor, GPU, armazenamento)
- ☐ Análise jurídica ou compliance (LGPD, etc.)
- ☐ Garantia de segurança absoluta
- ☐ Desenvolvimento de aplicações customizadas
- ☐ Integração com sistemas legados (escopo separado)

---

## 15. Plano de Implantação

| Fase | Atividade | Duração Estimada | Responsável |
|------|-----------|------------------|-------------|
| 1 | Preparação do ambiente (hardware + SO + Docker) | 1-2 dias | Cliente |
| 2 | Instalação do appliance | 1 dia | Fornecedor |
| 3 | Configuração de modelos e planos | 1 dia | Fornecedor |
| 4 | Validação técnica (scripts de readiness) | 1 dia | Conjunto |
| 5 | Treinamento da equipe administradora | 1 dia | Fornecedor |
| 6 | Homologação com dados do cliente | 3-5 dias | Conjunto |
| 7 | Produção assistida | 2 dias | Fornecedor |
| 8 | Handoff para operação do cliente | 1 dia | Fornecedor |

**Duração total estimada:** 10-15 dias úteis.

---

## 16. Critérios de Aceite

O sistema será considerado aceito quando:

1. [ ] API `/v1/chat/completions` responde corretamente (streaming e não-streaming)
2. [ ] API `/v1/rag/query` retorna respostas baseadas em documentos indexados
3. [ ] API `/v1/models` lista modelos configurados
4. [ ] Admin Dashboard exibe saúde dos serviços e consumo de tokens
5. [ ] Client Portal permite visualizar consumo e gerar API keys
6. [ ] Rate limiting bloqueia requisições que excedem cota
7. [ ] Billing gera faturas e permite confirmação manual de pagamento
8. [ ] Isolamento multi-tenant validado (cliente A não acessa dados do cliente B)
9. [ ] Backup e restore funcionam
10. [ ] Relatório de readiness indica verde para todos os itens críticos

---

**Este documento é um template e deve ser personalizado para cada cliente.**
**Consulte o time jurídico antes de assinar.**
