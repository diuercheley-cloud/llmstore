---
owner: platform-ops
status: consolidated
---

# FAQ — Demonstração Comercial llm-inference-stack

> **Aviso:** Este documento responde perguntas frequentes sobre o appliance local.
> **Dados exibidos em demonstração são fictícios** — nenhuma informação representa dados reais de clientes ou operações financeiras.
> **Todos os dados desta demonstração são fictícios.**
> **Esta demonstração utiliza dados fictícios — nenhuma informação real de clientes é exibida.**
> Billing é manual/local — sem PSP/PIX real.
> Este material não substitui análise jurídica ou de compliance.

---

### Os dados da demo são reais?
Não. **Todos os dados exibidos nesta demonstração são fictícios**, criados para simular cenários de uso. Nenhum dado de cliente real, paciente real ou transação financeira real é utilizado.

### Roda sem internet?

Sim. Uma vez instalado e com o modelo GGUF baixado, a stack opera 100% **air-gapped** (sem acesso à internet). O Docker, PostgreSQL, Redis e o modelo de IA rodam todos localmente. A única exceção é se você optar por baixar modelos adicionais depois — nesse caso precisará de internet temporária ou transferência manual do arquivo GGUF.

### Precisa de GPU?

**Recomendamos GPU NVIDIA** (RTX 3060+ ou superior) para performance adequada em produção. A stack funciona **apenas em CPU**, mas a velocidade de geração de tokens será significativamente menor. Para testes e homologação, CPU é suficiente. Em produção com múltiplos usuários, GPU é essencial.

### Quais modelos suporta?

Qualquer modelo no formato **GGUF** (suportado pelo llama.cpp). Exemplos testados:

- **Gemma 4** (modelo padrão recomendado)
- **Llama 3 / 3.1** (8B, 70B, 405B)
- **Mistral / Mixtral**
- **Qwen 2.5**
- **Phi-3 / Phi-4**
- **DeepSeek**
- **Qualquer GGUF compatível com llama.cpp**

Você adiciona modelos pela UI do Admin Lab (aba Modelos) ou copiando o arquivo `.gguf` para a pasta `models/` e registrando via API. Não é necessário rebuildar containers.

### Como controla custo?

O sistema oferece múltiplos mecanismos de controle:

1. **Planos de consumo:** Definem cotas mensais de tokens, RPM e RPD por cliente
2. **Rate limiting:** Limita requisições por minuto por cliente
3. **Bloqueio automático:** Cliente suspenso se exceder cota ou ficar inadimplente
4. **Faturas mensais:** Geradas automaticamente com base no consumo real
5. **Dashboard de uso:** Administrador e cliente acompanham consumo em tempo real

### Como evita vazamento de dados?

A stack é **100% local**. Não há envio de prompts, respostas, documentos ou metadados para servidores externos. Medidas adicionais:

- API keys armazenadas com hash (bcrypt)
- Isolamento multi-tenant (cada cliente com índice RAG e cotas próprios)
- Rate limiting por cliente
- Sem telemetria externa por padrão
- Relatórios de segurança para diagnóstico de exposição

**Importante:** Não garantimos segurança absoluta. Consulte seu time de segurança e compliance.

### Como faz backup?

```bash
./scripts/backup.sh
```

O script realiza dump do banco PostgreSQL (clientes, consumo, faturas, configurações) e preserva a estrutura. Para restore:

```bash
./scripts/restore.sh /caminho/para/postgres.dump
```

Consulte `docs/DISASTER_RECOVERY_LOCAL.md` e `docs/RETENTION_LOCAL.md` para política de retenção e recuperação.

### Como atualiza?

O processo de upgrade é documentado em `docs/UPGRADE_ROLLBACK_LOCAL.md`. O fluxo resumido:

1. Faça backup (`./scripts/backup.sh`)
2. Baixe a nova versão do repositório
3. Execute `./scripts/upgrade-local.sh`
4. Valide com `./scripts/validate-e2e.sh`

Rollback também é suportado via restore do backup e versão anterior.

### Como cria clientes?

Via Admin API ou script:

```bash
./scripts/create-client.sh nome-cliente "descrição do cliente"
```

Ou via Admin Lab (UI). Cada cliente recebe:

- Client ID único
- Plano de consumo (cota de tokens, RPM, RPD, contexto máximo)
- API key inicial
- Acesso ao Client Portal
- Índice RAG isolado

### Como funciona billing?

O billing é **local/manual** — sem integração com PSP/PIX real.

1. O sistema contabiliza tokens consumidos por cliente
2. No dia do fechamento (configurável), gera faturas automaticamente
3. O administrador visualiza as faturas no Admin Lab
4. O pagamento é recebido por fora (boleto, TED, contrato)
5. O administrador marca a fatura como paga manualmente:
   ```bash
   ./scripts/mark-invoice-paid.sh UUID_DA_FATURA local-ref-001
   ```
6. Clientes com faturas vencidas são suspensos automaticamente após tolerância configurável

### Suporta OpenAI SDK?

Sim. **100% compatível**. Basta alterar a URL base:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:18080/v1",
    api_key="sk-demo-xxxx"
)
```

Endpoints compatíveis:
- `GET /v1/models`
- `POST /v1/chat/completions` (streaming e não-streaming)
- `POST /v1/embeddings`
- `POST /v1/responses` (OpenAI Responses API)

### Suporta LangChain / Open WebUI / n8n?

Sim. Todos funcionam apontando a URL base da OpenAI para `http://localhost:18080/v1`:

**LangChain:**
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:18080/v1",
    api_key="sk-demo-xxxx",
    model="unsloth/gemma-4-E4B-it-GGUF"
)
```

**Open WebUI:** Configure em Settings > Connections > OpenAI API URL como `http://localhost:18080/v1`.

**n8n:** Use o nó OpenAI credencial com Base URL customizada `http://localhost:18080/v1`.

**AnythingLLM:** Configure o provider OpenAI com a URL base do stack.

---

## Perguntas Técnicas

### Quais portas são expostas?

| Porta | Serviço | Observação |
|-------|---------|------------|
| 18080 | Control Plane | Interface principal (API + UIs) |
| 5432 | PostgreSQL | Interno, não exposto externamente |
| 6379 | Redis | Interno, não exposto externamente |
| 9090 | Prometheus | Opcional (observability profile) |
| 3001 | Grafana | Opcional (observability profile) |

### Quais são as URLs padrão?

| Interface | URL |
|-----------|-----|
| Admin Dashboard | http://localhost:18080/admin-dashboard |
| Admin Lab | http://localhost:18080/admin-lab |
| Client Portal | http://localhost:18080/client-portal |
| Landing Page | http://localhost:18080/ |
| API | http://localhost:18080/v1 |

### Posso usar HTTPS?

Sim. Em modo produção (`STACK_MODE=prod`), o Caddy é utilizado como reverse proxy com suporte a Let's Encrypt para HTTPS automático.

### Como funciona o rate limiting?

O rate limiting é por cliente, configurado no plano:
- **RPM:** Requisições por minuto
- **RPD:** Requisições por dia
- Implementado com Redis (sliding window)
- Cliente que excede limite recebe HTTP 429

### Como funciona a fila de inferência?

Quando o data plane está ocupado, as requisições entram em fila:
- Timeout configurável por requisição
- Priorização não implementada nesta versão (FIFO)
- Máximo de gerações simultâneas configurável
- Circuit breaker protege contra data plane lento


**Q: Como posso obter um orçamento estimado durante a demo?**
A: O operador técnico pode gerar uma prévia de orçamento instantânea através do Admin Dashboard, selecionando o plano e os opcionais desejados (RAG, TTS, Suporte). Note que estes valores são configurados localmente para fins de demonstração e não representam uma oferta vinculativa final.
