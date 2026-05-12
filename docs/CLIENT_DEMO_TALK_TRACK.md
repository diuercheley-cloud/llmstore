# Talk Track — Falas Prontas para Demonstração Comercial

> **Use este guia durante a demo para garantir consistência na comunicação.**
> Adapte o tom conforme o perfil do interlocutor (técnico vs. executivo).

---

## Abertura da Reunião

### Versão Executiva (1 min)
"Olá, obrigado pela presença. Hoje vou apresentar o **Local AI Appliance** — um appliance local de IA que oferece API compatível com OpenAI, RAG, TTS e portal do cliente, tudo rodando dentro da sua infraestrutura. Dados fictícios na demo. Billing local e manual — sem PSP/PIX integrado. Vamos direto ao ponto?"

### Versão Técnica (2 min)
"Olá, vou demonstrar nossa plataforma local de LLM-as-a-Service. A stack expõe uma API 100% compatível com OpenAI — `/v1/chat/completions`, `/v1/embeddings`, `/v1/models` — com RAG, TTS e billing local. Tudo on-premise. O control plane gerencia autenticação, rate limiting, multitenancy e fila. O data plane roda inferência com llama.cpp. Esta demo usa dados fictícios e o billing é manual, sem PSP/PIX real. Vamos ver cada componente?"

---

## Explicar "Appliance Local"

"**Appliance local** significa que o sistema completo — API, banco de dados, fila, modelo de IA, TTS, RAG — roda **dentro do seu data center, servidor ou estação de trabalho**. Não há dependência de nuvem pública. Uma vez instalado e com o modelo baixado, ele pode operar 100% air-gapped, sem internet. Você tem soberania total sobre seus dados."

---

## Explicar Limitações

"É importante ser transparente sobre limitações:

- **Modelos locais são menores que GPT-4/Gemini/Claude.** Entregamos qualidade excelente para 90% dos casos de uso (suporte, análise de documentos, RAG, assistentes internos), mas para tarefas que exigem raciocínio extremamente complexo ou criatividade de ponta, modelos maiores em nuvem podem ser superiores.

- **Billing é manual.** Não há PSP/PIX real integrado. O sistema gera faturas e você confirma pagamento manualmente. Para automação futura, planejamos integração com PSPs.

- **Performance depende do hardware.** GPU dedicada (NVIDIA) oferece a melhor experiência. CPU é possível mas mais lento.

- **Não garantimos segurança absoluta.** Fornecemos relatórios de readiness e security scanning, mas cada cliente deve fazer sua própria análise de compliance."

---

## Explicar "Sem PSP/PIX Real"

"Esclarecendo o billing: o sistema **contabiliza o uso** de tokens por cliente, gera **faturas** automaticamente com valores calculados conforme o plano contratado, e o **administrador marca o pagamento manualmente**. Não há gateway de pagamento integrado (Stripe, Asaas, PIX real). O fluxo é:

1. Sistema gera invoice com valor devido
2. Cliente paga por fora (boleto, TED, contrato)
3. Administrador confirma no sistema
4. Invoice é marcada como paga

Isso é intencional para ambientes locais onde o financeiro já tem processo estabelecido."

---

## Explicar Segurança e Privacidade

"A stack foi projetada com segurança em mente, mas **não prometemos segurança absoluta**:

- **Dados nunca saem da sua rede** — toda inferência, armazenamento e indexação RAG são locais.
- **API keys armazenadas com hash** — nem o administrador vê a chave original após a criação.
- **Isolamento multi-tenant** — cada cliente tem seu índice RAG, cotas e chaves.
- **Rate limiting e bloqueio** — proteção contra abuso por cliente.
- **Relatórios de segurança** — scripts que varrem o sistema por secrets expostos, permissões incorretas e portas abertas.

**Importante:** Isso não substitui uma análise de compliance ou auditoria de segurança. Recomendamos que seu time de segurança avalie o appliance antes de colocar em produção com dados reais."

---

## Falas para Cada Tela

### Ao Abrir o Admin Dashboard

*Ação: Navegue para http://localhost:18080/admin-dashboard*

"Este é o **Admin Dashboard** — o centro de comando do appliance. Aqui você vê em tempo real:

- **Saúde dos serviços:** PostgreSQL, Redis, data plane, control plane — todos com indicador verde/amarelo/vermelho.
- **Clientes ativos:** Quantos tenants estão usando o sistema agora.
- **Consumo de tokens:** Hoje, este mês, projeção.
- **Requisições:** Total, por minuto, taxa de erro.
- **Latência:** Média e percentis.

Tudo monitorado localmente — sem enviar métricas para fora. Os dados exibidos são fictícios para esta demonstração."

### Ao Abrir o Admin Lab — Modelos (`http://localhost:18080/admin-lab`)

"Aqui no **Admin Lab**, aba Modelos, o administrador gerencia o catálogo de modelos de IA:

- Lista modelos disponíveis com alias, arquivo GGUF, status (ativo/inativo)
- Adiciona novo modelo selecionando arquivo GGUF da pasta `/models`
- Testa prompt diretamente pela UI
- Troca o modelo padrão sem reiniciar a stack
- Registra backend externo (LM Studio, Ollama, etc.)

Tudo sem precisar acessar o terminal do servidor."

### Ao Abrir o Admin Lab — Financeiro

"Aba Financeiro do Admin Lab:

- **Invoices em aberto:** Faturas aguardando pagamento
- **Invoices vencidas:** Clientes em atraso
- **Histórico de pagamentos:** Registro de todas as confirmações manuais

Lembrando: **não há PSP/PIX real**. O pagamento é confirmado manualmente pelo administrador após recebimento comprovado por canais externos."

### Ao Abrir o Client Portal (`http://localhost:18080/client-portal`)

"Este é o **Client Portal** — o que cada cliente/departamento vê:

- **Dashboard:** Consumo diário e mensal, cota restante, requests no período
- **API Keys:** Gerar nova chave, ver prefixo das chaves existentes, rotacionar
- **Invoices:** Visualizar faturas emitidas e pagas
- **Playground:** Testar prompts rapidamente

Cada cliente vê **apenas seus dados**. O isolamento é total."

### Ao Gerar uma API Key no Portal

"Ao clicar em 'Gerar chave', a API key é exibida **uma única vez**. O cliente deve copiá-la imediatamente. Depois disso, apenas o prefixo fica visível — nem o administrador consegue recuperar a chave original. Segurança desde o provisionamento."

### Ao Executar uma Chamada de API

"Agora vou mostrar a compatibilidade com OpenAI. Veja como é simples:"

```bash
curl -N http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Teste de integração."}],
    "max_tokens": 128,
    "stream": false
  }'
```

"**A única diferença** para a API da OpenAI é a URL base (`http://localhost:18080/v1` em vez de `https://api.openai.com/v1`) e a API key. Todo o resto — formato, headers, parâmetros, streaming — é idêntico. Zero retrabalho."

### Ao Executar Query RAG

"Vou demonstrar o **RAG — Retrieval-Augmented Generation**."

```bash
curl -fsS http://localhost:18080/v1/rag/query \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual o procedimento para queixa de dor torácica?",
    "top_k": 3
  }'
```

"O motor RAG busca nos documentos indexados os trechos mais relevantes, monta o contexto e o modelo gera a resposta final. Documentos internos nunca saem da sua rede. Os documentos desta demo são fictícios — criados para simulação."

### Ao Gerar Áudio TTS

"Vou gerar áudio localmente, sem chamar serviço externo:"

```bash
curl http://localhost:18080/pocket-tts/tts \
  -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"text": "Bem-vindo ao sistema de voz local."}'
```

"O TTS é 100% local. Útil para call centers, assistentes de voz, IVR, acessibilidade — sem depender de Google Cloud TTS ou Azure Speech."

### Ao Mostrar Security Report

"O **security report** varre o appliance em busca de:

- Secrets expostos em arquivos (API keys, tokens)
- Permissões incorretas em scripts e diretórios
- Portas expostas desnecessariamente
- Artefatos sensíveis

O resultado é um relatório em `artifacts/` com cada item classificado por severidade. Use como insumo para sua governança de segurança — mas **não substitui uma auditoria formal**."

### Ao Mostrar Readiness Report

"O **readiness report** valida se o sistema está pronto para produção:

- Conectividade com banco, Redis e data plane
- Modelo ativo e respondendo
- CORS configurado para appliance local
- Backup recente
- Rate limiting ativo
- Isolamento multi-tenant funcionando

Cada item recebe um status: ✅ verde (ok), 🟡 amarelo (atenção), 🔴 vermelho (falha)."

---

## Fala de Fechamento

"Recapitulando o que vimos hoje:

1. **API OpenAI-compatible** — suas aplicações funcionam sem mudanças
2. **RAG** — respostas baseadas em documentos internos, localmente
3. **TTS** — voz sem dependência cloud
4. **Portal do Cliente** — autoatendimento com isolamento total
5. **Admin Dashboard** — monitoria completa on-premise
6. **Billing Local/Manual** — faturamento sem PSP/PIX real
7. **Security & Readiness** — relatórios para suporte à compliance

**Dados fictícios nesta demonstração.** O sistema é appliance local — dados não saem da sua rede. **Não prometemos segurança absoluta.** Consulte sua equipe jurídica para compliance LGPD e demais regulamentações.

**Próximos passos:** Prova de conceito com dados não sensíveis do cliente, definição de hardware, escolha do plano, instalação assistida."

---

## Respostas Rápidas para Perguntas Frequentes Durante a Demo

| Pergunta | Resposta |
|----------|----------|
| "Roda sem internet?" | "Sim. Instalado e com o modelo baixado, opera 100% off-line." |
| "Precisa de GPU?" | "Recomendamos GPU NVIDIA, mas funciona em CPU. A diferença é performance." |
| "Quantos clientes suporta?" | "Centenas. Cada cliente com chave, cotas e RAG isolados." |
| "Tem PIX?" | "Não. O billing é manual/local. Você gera a fatura e marca como paga." |
| "Dados ficam seguros?" | "Ficam na sua rede. Não enviamos nada para fora. Mas não garantimos segurança absoluta." |
| "Suporta LangChain?" | "Sim. Basta apontar base_url para http://localhost:18080/v1." |
| "Qual modelo usa?" | "Gemma 4, Llama 3, Mistral — qualquer GGUF. Você escolhe e troca pela UI." |

---

## Follow-up Imediato

Após a demo, você pode gerar a proposta personalizada para o cliente em segundos para envio imediato:

```bash
make generate-proposal COMPANY_NAME="Nome do Cliente" SEGMENT="Segmento do Cliente"
```

Isso gera um arquivo Markdown profissional em `artifacts/proposals/` pronto para ser revisado e enviado.
