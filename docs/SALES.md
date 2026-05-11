# SaaS Sales Flow

## Objetivo

Transformar o stack em um produto vendavel com onboarding self-serve, plano free limitado, pagina publica de oferta e deploy simples em VPS.

### Technical Readiness & Safety
O sistema inclui ferramentas de auto-diagnóstico para garantir o sucesso da venda:

- **Pre-Demo Checklist**: `make pre-demo-check` (Garante que a demo não falhe ao vivo).
- **Pre-Client Checklist**: `make pre-client-check` (Valida segurança e performance antes da entrega).
- **Security Report**: Relatório detalhado de mitigação de riscos.

## Fluxo comercial

1. O visitante acessa `/` para entender a proposta do produto.
2. O visitante compara planos em `/pricing`.
3. O cadastro acontece em `/signup` ou direto no endpoint `POST /public/signup`.
4. O control plane cria o cliente, associa o plano e gera uma API key inicial.
5. O cliente usa a chave em `/v1/*` e acompanha uso, invoices e teste de prompt em `/client-portal`.

## Onboarding automatico

O endpoint `POST /public/signup` retorna:

- `client_id`
- `account_name`
- `plan_code`
- `api_key`
- `portal_url`
- `api_base_url`

A API key e retornada apenas uma vez. O cliente deve armazenar esse valor no momento do cadastro.

## Oferta comercial padrao (Local Edition)

O sistema utiliza faturamento local/manual nesta versão.

| Recurso | Free | Basic | Pro | Enterprise Local |
| :--- | :--- | :--- | :--- | :--- |
| **Requisições (RPM/RPD)** | 10 / 100 | 30 / 1.000 | 60 / 5.000 | 300 / 1.000.000 |
| **Tokens (Mês)** | 50.000 | 500.000 | 5.000.000 | 50.000.000 |
| **Contexto Máximo** | 4.096 | 8.192 | 16.384 | 131.072 |
| **Streaming** | Sim | Sim | Sim | Sim |
| **RAG** | Não | Sim (5 docs) | Sim (50 docs) | Sim (1.000 docs) |
| **TTS** | Não | Sim | Sim | Sim |
| **Embeddings** | Não | Sim | Sim | Sim |
| **Exportação de Uso** | Não | Não | Sim | Sim |
| **Suporte** | Comunitário | E-mail | E-mail Prioritário | 24/7 Dedicado |

**Nota:** O faturamento é realizado de forma manual/local. Não há integração direta com PSP/PIX nesta versão.

## Deploy publico

Em producao, use `STACK_MODE=prod` e `scripts/deploy-vps.sh`. O compose de producao sobe o Caddy na frente do control plane para obter HTTPS automatico com Let's Encrypt.

## Demo Pack Comercial

O `demo-pack/` contem um pacote completo de demonstracao com 5 cenarios comerciais ficticios. Use durante reunioes de vendas para demonstrar o valor do produto sem precisar configurar dados manualmente.

```bash
# Preparar ambiente de demonstracao
make demo-pack

# Executar validacao
make validate-demo-pack
```

Documentacao completa da demonstracao em `demo-pack/demo-flow.md` (roteiro de 30-45 min).

### Cenarios de venda

| Cenario | Problema | Solucao |
|---------|----------|---------|
| Clinica Local | LGPD, dados sensiveis | Inferencia local + RAG + compliance |
| Escritorio Juridico | Sigilo advocaticio | Stack local sem nuvem |
| Suporte Tecnico | knowledge base dispersa | RAG + TTS + chat |
| Escola/Treinamento | Orcamento limitado | Plano a partir de R$ 197/mes |
| Provedor de API | Concorrer com OpenAI | Plataforma completa white-label |

### Recursos de apoio

- `demo-pack/demo-objection-handling.md` - Respostas para 15+ objecoes comuns
- `demo-pack/demo-api-requests.md` - Requisicoes curl prontas para cada endpoint
- `demo-pack/demo-prompts.md` - Prompts por cenario
- `demo-pack/demo-flow.md` - Roteiro completo da reuniao

### Documentos de Apresentação para Clientes

Material adicional para reuniões comerciais e técnicas com clientes:

- [Roteiro de Apresentação (15/30/60 min)](docs/CLIENT_PRESENTATION_SCRIPT.md) — 3 versões de roteiro
- [Talk Track — Falas Prontas](docs/CLIENT_DEMO_TALK_TRACK.md) — Roteiro textual completo
- [FAQ da Demo Comercial](docs/CLIENT_DEMO_FAQ.md) — Perguntas frequentes sobre o appliance
- [Objeções Comuns](docs/CLIENT_DEMO_OBJECTIONS.md) — Respostas para 10+ objeções

### Propostas Comerciais e Técnicas

Templates de propostas em Markdown para envio formal a clientes:

- [Proposta Técnica](proposals/TECHNICAL_PROPOSAL_TEMPLATE.md) — Completa: arquitetura, componentes, requisitos, segurança, implantação
- [Proposta Comercial](proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md) — Problema, solução, planos (placeholders), cronograma, suporte
- [One-Pager Executivo](proposals/LOCAL_AI_APPLIANCE_ONE_PAGER.md) — Resumo de página única para apresentação rápida

Geração de PDF local:
```bash
./scripts/generate-proposal-pdf.sh \
  --input proposals/TECHNICAL_PROPOSAL_TEMPLATE.md \
  --output proposals/generated/proposta-tecnica.pdf
```

## Operacao de venda

- Use a landing como CTA principal.
- Direcione campanhas para `/pricing`.
- Entregue trial ou free via `/signup`.
- Faca upgrade de plano pelo Admin API ou pelo fluxo comercial interno.
- Use o **Demo Pack Comercial** para reunioes com clientes potenciais.
