---
owner: platform-ops
status: consolidated
---

# Roteiro de Apresentação Comercial — Local AI Appliance

> **Aviso importante:** Esta demonstração utiliza **dados fictícios** para fins ilustrativos. Nenhuma informação exibida representa dados reais de pacientes, clientes ou operações financeiras. O sistema opera em **modo appliance local** — toda inferência, armazenamento e processamento ocorrem dentro da infraestrutura do cliente. O billing é **local/manual** e **não inclui PSP/PIX real**. Este material não substitui análise jurídica ou de compliance.
>
> Para validacao E2E automatica da demo antes da apresentacao:
> ```bash
> ./scripts/validate-commercial-demo-e2e-local.sh --seed-demo --skip-tts --skip-rag
> ```

---

## Roteiro de 15 Minutos

### Abertura (1 min)
"Olá, hoje vou apresentar o llm-inference-stack — um appliance local de LLM-as-a-Service. Ele oferece API compatível com OpenAI, RAG, TTS, portal do cliente e painel administrativo, tudo rodando 100% na sua infraestrutura. Nenhum dado sai da sua rede. O faturamento é local e manual. Vamos à demonstração com dados fictícios de exemplo."

### Problema e Proposta de Valor (2 min)
"Empresas enfrentam três desafios com IA: vazamento de dados ao usar APIs públicas, custos imprevisíveis por token, e dificuldade de integração com sistemas internos. Nossa stack resolve tudo entregando uma plataforma OpenAI-compatible local, com controle total sobre dados, custos previsíveis via planos manuais, e pronta para uso em minutos."

### Demo: Admin Dashboard (3 min)
*Ação: Abra http://localhost:18080/admin-dashboard*
"Aqui o administrador vê saúde do sistema, uso por cliente, latência e erros. Tudo em tempo real, sem depender de SaaS externo."

### Demo: Client Portal (2 min)
*Ação: Abra http://localhost:18080/client-portal*
"Cada cliente tem seu portal para ver consumo, gerar chaves de API e consultar faturas. O isolamento entre clientes é total — cada um vê apenas seus próprios dados."

### Demo: API OpenAI-compatible (2 min)
*Ação: Execute curl para /v1/chat/completions*
"Qualquer aplicação que use OpenAI SDK funciona trocando apenas a URL base. A resposta vem do modelo local, sem enviar dado algum para nuvem."

### Demo: RAG (2 min)
*Ação: Execute /v1/rag/query*
"Documentos internos são indexados localmente. O modelo responde com base nesses documentos, garantindo que conhecimento proprietário nunca saia da sua rede."

### Fechamento (2 min)
"Em resumo: API OpenAI-compatible local, RAG, TTS, billing manual, portal do cliente, isolamento multi-tenant. Dados fictícios nesta demo. Próximo passo: agendarmos um piloto com dados reais do seu cenário."

### Próximos Passos (1 min)
- Agendar prova de conceito com dados do cliente
- Definir requisitos de hardware (GPU recomendada, CPU possível)
- Estimar plano conforme volume mensal de tokens

---

## Roteiro de 30 Minutos

### Abertura (1 min)
"Olá, hoje vou apresentar o Local AI Appliance — um appliance local de LLM-as-a-Service. API compatível com OpenAI, RAG, TTS, billing local/manual, portal do cliente e admin dashboard. Tudo on-premise. Os dados desta demo são fictícios. O sistema não inclui PSP/PIX real — o faturamento é manual. Vamos começar?"

### Apresentação do Problema (3 min)
"Três problemas principais: (1) Dados sensíveis trafegando por APIs públicas de IA — todo prompt enviado ao ChatGPT ou OpenAI API sai da sua rede. (2) Custos imprevisíveis — sem controle de budget, cada funcionário pode gerar despesas inesperadas. (3) Complexidade operacional — montar um stack local de IA exige GPU, CUDA, llama.cpp, Kubernetes... entregamos isso pronto, como appliance."

### Proposta de Valor (2 min)
"Nosso appliance local oferece: (a) API 100% compatível com OpenAI — zero retrabalho. (b) RAG nativo para indexar documentos internos sem enviar dados externos. (c) TTS local — geração de áudio sem chamadas externas. (d) Multitenancy com isolamento — cada departamento ou cliente com seu plano, chave e billing. (e) Billing local/manual — sem dependência de PSP/PIX. Tudo on-premise."

### Demo: Admin Dashboard (5 min)
*Ação: Abra http://localhost:18080/admin-dashboard*
"Aqui temos o painel do administrador. Mostra: clientes ativos, saúde dos serviços (PostgreSQL, Redis, data plane), consumo de tokens hoje e no mês, requisições recentes, latência média e erros. Tudo live. Sem agentes externos, sem SaaS de monitoria — Prometheus e métricas embutidos. Dados são fictícios para demonstração."

*Ação: Navegue até Admin Lab em http://localhost:18080/admin-lab*
"No Admin Lab, o administrador gerencia modelos (ativa/desativa, testa prompts), vê faturas em aberto, marca pagamentos manuais, consulta logs e health profundo. Tudo consolidado."

### Demo: Client Portal (4 min)
*Ação: Abra http://localhost:18080/client-portal*
"Cada cliente acessa seu portal com a API key. Aqui ele vê: consumo diário/mensal, cota restante, faturas emitidas e pagas, e pode gerar/rotacionar chaves de API. O portal é 100% isolado — cliente A não vê dados do cliente B."

### Demo: API OpenAI-compatible (4 min)
*Ação: Execute os curls abaixo no terminal*
```bash
# Listar modelos
curl -fsS http://localhost:18080/v1/models \
  -H "Authorization: Bearer ${API_KEY}" | python3 -m json.tool

# Chat completion
curl -N http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Explique RAG em 3 linhas."}],
    "max_tokens": 256,
    "stream": false
  }' | python3 -m json.tool
```
"Qualquer SDK OpenAI — Python, Node, LangChain, Open WebUI — funciona apenas alterando `base_url` para `http://localhost:18080`. Zero mudança de código. A inferência roda no modelo local GGUF."

### Demo: RAG — Retrieval-Augmented Generation (4 min)
*Ação: Execute query RAG*
```bash
curl -fsS http://localhost:18080/v1/rag/query \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual o protocolo para atendimento de emergência?",
    "top_k": 3
  }'
```
"Os documentos internos são indexados localmente. O modelo busca o contexto relevante antes de responder. Dados jamais saem da infraestrutura. Os documentos desta demo são fictícios — criados para simular uma clínica, escritório jurídico e suporte técnico."

### Demo: TTS — Text-to-Speech (2 min)
*Ação: Execute se habilitado*
```bash
curl -fsS http://localhost:18080/pocket-tts/tts \
  -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"text": "Bem-vindo ao sistema de voz local."}' \
  -o demo-audio.wav
```
"Geração de áudio 100% local — sem enviar texto para serviços cloud. Útil para call centers, assistentes de voz e acessibilidade."

### Demo: Billing Local/Manual (3 min)
*Ação: Mostre invoices no Admin Lab e marque uma como paga*
"O sistema gera faturas automaticamente baseado no consumo. O administrador confirma o pagamento manualmente. **Não há PSP/PIX real integrado.** O fluxo é: gerar invoice, receber pagamento por fora (boleto, transferência, contrato), marcar como pago no sistema. O cliente automaticamente volta a active se estava suspenso."

### Fechamento (2 min)
"Recapitulando: API OpenAI-compatible, RAG, TTS, portal do cliente, billing manual com planos, admin dashboard com monitoria completa. Tudo on-premise. Esta demo usou apenas dados fictícios. **Não prometemos segurança absoluta** — cada cliente deve fazer sua própria análise de compliance com LGPD e demais regulamentações."

### Próximos Passos (2 min)
1. Agendar prova de conceito de 1 semana com dados não sensíveis do cliente
2. Definir hardware: GPU NVIDIA recomendada (ex: RTX 4060+), CPU possível para testes
3. Escolher pacote: Free (teste), Basic, Pro ou Enterprise Local
4. Assinar contrato de suporte e definir SLA
5. Agendar instalação assistida

---

## Roteiro de 60 Minutos

### Abertura (2 min)
"Olá, hoje vou apresentar o llm-inference-stack — appliance local de LLM-as-a-Service. Nesta sessão de 60 minutos, vou mostrar cada capacidade do sistema com exemplos práticos. Dados são fictícios para demonstração. O sistema opera localmente — nada sai da sua rede. Billing é manual — sem PSP/PIX real. Vamos começar com uma visão do problema que resolvemos."

### Apresentação do Problema (5 min)
"O mercado de IA generativa cresceu rápido, mas as soluções disponíveis têm limitações sérias:

1. **APIs públicas (OpenAI, Anthropic, Google):** Seus prompts, documentos e dados de negócio saem da sua rede e são processados em servidores de terceiros. Para setores regulados (saúde, direito, finanças), isso é vedado ou requer contrato específico de DPA.

2. **Custos imprevisíveis:** Sem controle granular de budget por usuário/departamento, qualquer pessoa pode gerar custos exponenciais.

3. **Complexidade técnica:** Montar inferência local exige GPU, CUDA, llama.cpp, gestão de fila, rate limiting, multitenancy, billing. A maioria das empresas não tem essa engenharia disponível.

4. **Integração trabalhosa:** Migrar de OpenAI para um modelo local normalmente exige reescrever integrações. Nossa API é drop-in replacement.

**Nosso appliance resolve tudo isso em um pacote só."**

### Proposta de Valor (3 min)
"O llm-inference-stack entrega:

| Capacidade | Benefício |
|------------|-----------|
| API OpenAI-compatible | Zero retrabalho nas aplicações |
| RAG nativo | Respostas baseadas em documentos internos |
| TTS local | Voz sem dependência cloud |
| Multi-tenant isolado | Cada cliente/departamento com seu plano |
| Billing manual local | Controle de faturamento sem PSP/PIX |
| Admin Dashboard | Monitoria completa on-premise |
| Security Reports | Relatório de readiness e compliance |

Tudo on-premise. Dados nunca saem da sua rede."

### Demo: Admin Dashboard (10 min)

#### Visão Geral (5 min)
*Ação: Abra http://localhost:18080/admin-dashboard*
"O dashboard centraliza:

- **Serviços:** Status de PostgreSQL, Redis, data plane, control plane
- **Clientes:** Lista, planos, consumo atual vs. cota
- **Uso:** Gráfico de tokens por dia, requisições por minuto
- **Latência:** Média, P50, P95, P99
- **Erros:** Últimos erros por cliente, rate limit hits
- **Cache:** Hit rate do response cache

Navegue pelos cards. Tudo servido pelo próprio control plane — sem SaaS externo de monitoria."

#### Admin Lab — Modelos (3 min)
*Ação: Abra http://localhost:18080/admin-lab, aba Modelos*
"Aqui o administrador gerencia modelos sem precisar de shell: ativar/desativar, testar prompt, trocar default, registrar novo backend (LM Studio, Ollama, etc.). O sistema detecta automaticamente arquivos GGUF em /models."

#### Admin Lab — Financeiro (2 min)
*Ação: Abra aba Faturas no Admin Lab*
"Invoices geradas automaticamente por consumo. O administrador pode:
- Visualizar faturas em aberto, vencidas e pagas
- Marcar pagamento manual (sem PSP/PIX real)
- Cancelar invoice
- Ver extrato por cliente"

### Demo: Client Portal (8 min)

*Ação: Abra http://localhost:18080/client-portal*
"O portal do cliente é o que cada tenant vê. Mostro cada seção:

1. **Dashboard de Consumo:** Tokens usados hoje, este mês, cota restante, requisições
2. **API Keys:** Gerar, listar prefixos, rotacionar, revogar
3. **Faturas:** Histórico de invoices pagas e a pagar
4. **Playground:** Testar prompts diretamente no navegador
5. **Uso por Modelo:** Detalhamento de custo por modelo consumido

*Ação: Gere uma nova API key no portal*
"Veja como é simples — um clique, a chave aparece uma única vez, o cliente copia e começa a usar."

"Isolamento total: cada cliente autentica com Bearer token. O admin nunca expõe ADMIN_TOKEN para cliente. Os dados de um cliente jamais são visíveis a outro."

### Demo: API OpenAI-compatible (8 min)

#### Integração Básica (3 min)
```bash
# Listar modelos
curl http://localhost:18080/v1/models \
  -H "Authorization: Bearer ${API_KEY}"

# Chat completion (streaming)
curl -N http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "O que é um appliance local?"}],
    "max_tokens": 256,
    "stream": true
  }'
```

#### OpenAI Python SDK (2 min)
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
print(response.choices[0].message.content)
```

#### LangChain (2 min)
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:18080/v1",
    api_key="sk-demo-xxxx",
    model="unsloth/gemma-4-E4B-it-GGUF"
)
```

#### Open WebUI / n8n (1 min)
"Configure a conexão no Open WebUI ou n8n apontando para `http://localhost:18080/v1` com a API key do cliente. Compatibilidade total com OpenAI."

### Demo: RAG — Retrieval-Augmented Generation (8 min)

#### Conceito (2 min)
"RAG permite que o modelo responda com base em documentos internos que você fornece. Diferente de fine-tuning, não requer retreinar o modelo — apenas indexa os documentos e busca o contexto relevante a cada pergunta."

#### Indexação (2 min)
"A indexação é feita via API ou pelo script `./scripts/seed-rag-documents.sh`. Documentos suportados: TXT, PDF, Markdown. Cada cliente tem seu próprio índice RAG isolado."

#### Query (2 min)
```bash
curl -fsS http://localhost:18080/v1/rag/query \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual o procedimento para queixa de dor torácica?",
    "top_k": 3
  }'
```
"O motor RAG busca os documentos mais relevantes, monta o contexto e o modelo gera a resposta — tudo localmente."

#### Validação (2 min)
"Para garantir que o RAG está funcionando: `./scripts/validate-rag-local-multiclient.sh`. Testa isolamento entre clientes — cliente A não acessa documentos do cliente B."

### Demo: TTS — Text-to-Speech (5 min)

*Ação: Execute se habilitado*
```bash
# Health check
curl http://localhost:18080/pocket-tts/health

# Gerar áudio
curl http://localhost:18080/pocket-tts/tts \
  -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"text": "Esta é uma demonstração de texto para voz do nosso appliance local."}' \
  -o /tmp/demo-tts.wav

# Reproduzir (Linux)
aplay /tmp/demo-tts.wav
```
"TTS 100% local — ideal para call centers, centrais de atendimento e acessibilidade onde dados não podem sair da empresa. Não usa Google Cloud TTS, Azure Speech ou qualquer serviço externo."

### Demo: Embeddings / Responses API (5 min)

*Ação: Execute se habilitado*

#### Embeddings
```bash
curl http://localhost:18080/v1/embeddings \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Texto para gerar embedding",
    "model": "text-embedding-3-small"
  }'
```

#### Responses API (OpenAI Responses beta)
```bash
curl http://localhost:18080/v1/responses \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "input": "Resuma o conceito de appliance local"
  }'
```
"Embeddings para busca semântica própria e Responses API seguindo o padrão OpenAI — mesmo contrato de API, diferentes capacidades."

### Demo: Billing Local/Manual (5 min)

#### Geração de Faturas (2 min)
"A cada ciclo mensal, ou sob demanda, o administrador gera invoices:"
```bash
./scripts/generate-invoices.sh
```
"O sistema calcula o consumo de cada cliente, aplica a precificação do plano e gera invoices em `pending`."

#### Fluxo de Pagamento (2 min)
*Ação: Mostre no Admin Lab*
"As invoices aparecem no Admin Lab e no portal do cliente. O pagamento é feito fora do sistema (boleto, TED, contrato). O administrador confirma manualmente:"
```bash
./scripts/mark-invoice-paid.sh UUID_DA_FATURA local-ref-001
```

#### Suspensão por Inadimplência (1 min)
"Se o cliente não pagar no prazo configurado (padrão: 7 dias de vencimento + 15 de tolerância), ele é automaticamente suspenso — a API dele para de responder. Ao pagar e o admin confirmar, o acesso é restaurado."

### Demo: Security / Readiness Reports (5 min)

#### Relatório de Readiness (2 min)
```bash
./scripts/production-readiness-local.sh
```
"Gera relatório detalhado: conectividade, GPU, modelos, CORS, rate limiting, isolamento multi-tenant, backup. Cada item é verde/amarelo/vermelho com recomendações."

#### Security Report (2 min)
```bash
./scripts/security-report-local.sh
```
"Relatório de segurança: verifica secrets em arquivos, permissões, exposição de portas, artefatos sensíveis. Tudo documentado em `artifacts/security-report-<data>/`."

#### Diagnóstico de Advertências (1 min)
```bash
./scripts/diagnose-readiness-warnings-local.sh
```
"Explica cada warning e sugere ação corretiva."

### Fechamento (3 min)
"Vimos hoje:

1. **Admin Dashboard** — Monitoria completa on-premise
2. **Client Portal** — Autoatendimento para cada tenant
3. **API OpenAI-compatible** — Drop-in replacement
4. **RAG** — Respostas baseadas em documentos internos
5. **TTS** — Voz local sem dependência cloud
6. **Embeddings / Responses** — Capacidades adicionais
7. **Billing Local/Manual** — Faturamento sem PSP/PIX
8. **Security & Readiness** — Relatórios de compliance

**Lembretes importantes:**
- Esta demo usou dados fictícios — não representa clientes reais
- O sistema é appliance local — dados não saem da sua rede
- Billing é manual — não há PSP/PIX real integrado
- Não garantimos segurança absoluta — consulte sua equipe de compliance
- Este material não substitui análise jurídica

**Próximos passos concretos:**
1. Enviar proposta comercial conforme plano escolhido
2. Agendar instalação assistida (remota ou presencial)
3. Provisionar ambiente de homologação com dados do cliente
4. Treinamento da equipe de administração
5. Definição de SLA e suporte

Perguntas?"

---

## Pagina de Capacidades (/capabilities)

Mostre ao cliente a pagina de capacidades para demonstrar transparencia sobre recursos e limitacoes:

```bash
open http://localhost:18080/capabilities
```

**O que falar:** "Esta pagina lista todos os recursos do sistema com status claro — o que funciona e o que ainda esta em desenvolvimento. As limitacoes sao explicitas: nao temos PSP/PIX real e a performance depende do hardware local. Isso mostra nosso compromisso com transparencia."

## Comando Unico de Demo Comercial

```bash
# Preparar e validar a demo completa
make customer-demo

# Full demo com seed de dados
make customer-demo-full
```

Relatório gerado em `artifacts/customer-demo/<timestamp>/`.

## Guia Visual de Demonstração

Para uma demonstração padronizada com screenshots, storyboard e plano de captura, consulte o [Guia Visual de Demonstração](demo-visual-guide/README.md).

```bash
# Gerar plano de screenshots
make demo-screenshot-plan

# Validar guia visual
make validate-demo-visual-guide
```

## Apêndice: URLs de Referência

| Interface | URL |
|-----------|-----|
| Admin Dashboard | http://localhost:18080/admin-dashboard |
| Admin Lab | http://localhost:18080/admin-lab |
| Client Portal | http://localhost:18080/client-portal |
| Landing Page | http://localhost:18080/ |
| API Base | http://localhost:18080/v1 |
| Health | http://localhost:18080/health |
| Ready | http://localhost:18080/ready |
| Metrics | http://localhost:18080/metrics |

## Meeting Ready Check

Antes da reunião, execute o **Meeting Ready Check** para garantir que tudo está pronto:

```bash
make meeting-ready
```

Isso gera um relatório em `artifacts/meeting-ready/<timestamp>/` com checklist visual, URLs, comandos de emergência e confirmação de que todos os endpoints estão acessíveis.

```bash
# Validar o script
make validate-meeting-ready
```

## Apêndice: Scripts Úteis

| Operação | Comando |
|----------|---------|
| Validar demo completa | `./scripts/validate-e2e.sh` |
| Validar billing | `./scripts/validate-local-billing.sh` |
| Validar RAG | `./scripts/validate-rag-local-multiclient.sh` |
| Validar portal | `./scripts/validate-client-portal-local.sh` |
| Validar dashboard | `./scripts/validate-demo-admin-dashboard.sh` |
| Gerar faturas | `./scripts/generate-invoices.sh` |
| Marcar paga | `./scripts/mark-invoice-paid.sh` |
| Relatório readiness | `./scripts/production-readiness-local.sh` |
| Relatório segurança | `./scripts/security-report-local.sh` |
| Backup | `./scripts/backup.sh` |
| Criar cliente | `./scripts/create-client.sh` |
| Validar dados fictícios | `make validate-fake-data` |

## 8. Gestão Comercial (CRM Local)

- **Cenário**: Mostrar como a empresa gerencia o pipeline de vendas da própria solução.
- **Ação**: Navegar até a seção "Sales / Leads" no Admin Dashboard.
- **Destaque**: "Toda a gestão de leads é feita aqui mesmo, localmente. Não usamos CRM externo para garantir que nem mesmo os dados dos nossos potenciais clientes saiam da nossa infraestrutura."
- **Ação**: Mostrar um lead demo (ex: Clínica Horizonte), avançar o estágio e adicionar uma nota.
