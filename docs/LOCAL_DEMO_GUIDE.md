# Guia de Demonstração Local - llm-inference-stack

Este guia descreve como preparar e executar uma demonstração completa do produto em um ambiente local (como um notebook com WSL2), sem dependência de nuvem, domínios públicos ou gateways de pagamento reais.

## Objetivo da Demo
Demonstrar a soberania de dados, facilidade de implantação, portal do cliente, governança de API e billing manual, tudo rodando localmente com aceleração de GPU (quando disponível).

### Validacao E2E da Demo Comercial

Para validar o fluxo completo da demonstracao comercial (seed, validacao, meeting-ready, APIs, propostas, orcamentos, relatorios):

```bash
./scripts/validate-commercial-demo-e2e-local.sh --seed-demo
```

Flags disponiveis: `--skip-tts`, `--skip-rag`, `--reset-first`, `--base-url`.
Relatorio gerado em `artifacts/final-qa/commercial-demo-e2e/<timestamp>/`.

## Pre-Demo Checklist
Antes de iniciar a demonstração, execute o checklist automatizado para garantir que o ambiente está pronto:

```bash
make pre-demo-check
```

Isso gerará um relatório em `artifacts/pre-client-checklists/` validando saúde, segurança e prontidão dos dados de demo.

## Pré-requisitos
- Docker e Docker Compose instalados.
- WSL2 (se estiver no Windows) com drivers NVIDIA configurados.
- Modelo GGUF baixado em `./models/` (ex: `gemma-4-E4B-it-Q4_0.gguf`).
- Arquivo `.env` configurado com `ADMIN_TOKEN`.

## Como subir o sistema
1. Inicie a stack em modo de produção local:
   ```bash
   ./scripts/local-production-up.sh
   ```
2. Verifique se as interfaces estão acessíveis:
   ```bash
   ./scripts/ui-health.sh
   ```

## Matriz de Planos Comerciais
O sistema agora suporta 4 planos padrão com limites automatizados:
- **Free**: Ideal para testes, limitado a 100 requisições/dia.
- **Basic**: Para pequenos projetos, inclui RAG e TTS.
- **Pro**: Maior throughput e contexto de 16k tokens.
- **Enterprise Local**: Foco em alta escala local com 131k de contexto.

Para carregar os planos comerciais:
```bash
./scripts/seed-commercial-plans-local.sh
```

## Como carregar dados demo
O projeto inclui um script que provisiona automaticamente um cliente, plano, chaves de API, uso sintético e documentos RAG:
```bash
./scripts/seed-demo-local.sh
```
Este script salva as credenciais do cliente demo em `.local/demo-client.env`.

## Acessando as Interfaces

### Admin Dashboard
Utilizado para monitorar a saúde da stack, uso global e erros.
- **URL**: `http://localhost:18080/admin-dashboard`
- **Autenticação**: Requer o `ADMIN_TOKEN` configurado no `.env`.

### Admin Lab
Interface avançada para gestão de modelos, backends e financeiro.
- **URL**: `http://localhost:18080/admin-lab`
- **Destaque**: Mostre a aba de "Faturamento" para ver as faturas geradas.

### Client Portal
Onde o cliente final gerencia suas chaves e vê seu consumo.
- **URL**: `http://localhost:18080/client-portal`
- **Destaque**: Use a API Key gerada pelo `seed-demo-local.sh` (encontrada em `.local/demo-client.env`).

## Testando a API (OpenAI-compatible)
Você pode demonstrar a compatibilidade usando um simples `curl`:
```bash
source .local/demo-client.env
curl -N http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer $DEMO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [{"role": "user", "content": "Explique o que é soberania de dados em uma frase."}],
    "stream": true
  }'
```

## Testando TTS (Text-to-Speech)

O sistema agora possui suporte a voz totalmente governado por cotas:

1. Acesse o Client Portal.
2. Navegue até a seção de TTS.
3. Teste a geração de áudio.
4. Verifique no Dashboard como o uso de caracteres é descontado do seu limite diário/mensal.
5. Veja o item de TTS aparecer no Invoice Preview.

## Testando RAG (Recuperação Aumentada por Geração)
Se você executou o `seed-demo-local.sh`, documentos de exemplo foram indexados.
Teste a busca semântica:
```bash
source .local/demo-client.env
curl -s -X POST "http://localhost:18080/v1/rag/query" \
  -H "Authorization: Bearer $DEMO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual a política de retenção de dados da TechSolutions?"}'
```

## Billing Local/Manual
Demonstre como o sistema lida com faturamento sem precisar de um PSP (Stripe/Asaas):
1. No **Admin Lab**, vá em Faturamento.
2. Veja a fatura `pending`.
3. Simule o registro de pagamento manual:
   ```bash
   ./scripts/mark-invoice-paid.sh <UUID_DA_FATURA> local-manual-ref-001
   ```
4. Observe o status mudar para `paid` no portal do cliente.

## Observabilidade
Mostre o Grafana (se habilitado) ou as métricas brutas:
- **Métricas**: `http://localhost:18080/metrics`
- **Grafana**: `http://localhost:3001` (requer `./scripts/up.sh` com profile observability)

## Como resetar a demo
Para limpar todos os dados criados e voltar ao estado inicial:
```bash
./scripts/reset-demo-local.sh --yes
```

## Demo Pack Comercial

O **Demo Pack Comercial** estende a demonstração básica com 5 cenários comerciais fictícios prontos para apresentação a clientes.

### Cenários

1. **Clínica Local** - Compliance LGPD, prontuários fictícios, protocolos clínicos
2. **Escritório Jurídico** - Sigilo advocatício, contratos, jurisprudência fictícia
3. **Suporte Técnico** - Knowledge base, tickets, TTS para IVR
4. **Escola/Treinamento** - Material didático, correção de redações, tutor IA
5. **Provedor de API de IA** - Marketplace de modelos, multi-cliente, billing

### Como usar

```bash
# Carregar todos os dados demo (5 clientes + planos + RAG + invoices)
make demo-pack

# Validar tudo
make validate-demo-pack

# Acessar
open http://localhost:18080/admin-dashboard
```

### Arquivos do Demo Pack

- `demo-pack/demo-scenarios.json` - Cenários com problema, demonstração, endpoints e valor comercial
- `demo-pack/demo-clients.json` - Clientes e planos fictícios (legado)
- `demo-pack/demo-documents/` - Documentos RAG por cenário (legado)
- `demo-pack/demo-prompts.md` - Prompts sugeridos para cada cenário
- `demo-pack/demo-api-requests.md` - Requisições curl para demonstração
- `demo-pack/demo-objection-handling.md` - Objeções comuns e respostas
- `demo-pack/demo-flow.md` - Roteiro passo a passo (30-45 min)
- `demo-pack/fake-data/` - **Fonte oficial** de dados fictícios para seed e validação

### Reset (Modo Seguro)

O reset agora possui protecoes para evitar perda de dados reais:

```bash
# Modo padrao: --dry-run (apenas simula, nao apaga nada)
make reset-demo-pack

# Ver o que seria apagado (seguro)
./scripts/reset-commercial-demo-pack.sh --dry-run

# Reset real (exige confirmacao)
./scripts/reset-commercial-demo-pack.sh --yes

# Reset com limpeza completa (RAG, TTS, faturas, uso)
./scripts/reset-commercial-demo-pack.sh --yes --include-rag --include-tts --include-invoices --include-usage

# Validar seguranca do reset
make validate-reset-demo-pack
```

**Garantias de Seguranca:**
- `--dry-run` e o padrao (nunca apaga nada sem confirmacao)
- `--yes` obrigatorio para execucao real
- Nunca apaga clientes sem `metadata demo=true`
- Nunca apaga `models/`, `backups/`, `releases/`, `.env.local`, `exports/`
- Relatorio gerado em `artifacts/demo-reset/<timestamp>/`

**Opcoes avancadas:**
| Opcao | Descricao |
|-------|-----------|
| `--dry-run` | Modo simulacao (padrao) |
| `--yes` | Confirma e executa o reset real |
| `--include-rag` | Remove documentos RAG demo |
| `--include-tts` | Remove arquivos TTS demo |
| `--include-invoices` | Remove faturas demo |
| `--include-usage` | Remove registros de uso demo |
| `--demo-prefix` | Prefixo para planos/keys demo (padrao: `demo-`) |

Para recriar apos reset:
```bash
make demo-pack
```

## Pagina de Capacidades (/capabilities)

Durante a demonstracao, use a pagina de capacidades para mostrar ao cliente o que o sistema faz e suas limitacoes:

```bash
open http://localhost:18080/capabilities
```

A pagina exibe:
- **18 recursos** com status (Suportado, Parcial, Nao suportado) e observacoes
- **6 limitacoes** explicitas (PSP real, PIX real, Tools/FC parcial, hardware, HTTPS, seguranca)
- Versao atual do sistema carregada via API
- Links para todas as interfaces

Endpoint JSON: `GET /public/capabilities`

```bash
curl -s http://localhost:18080/public/capabilities | python3 -m json.tool
```

## Meeting Ready Check (Pré-Reunião)

Antes de apresentar o sistema ao cliente, execute o **Meeting Ready Check**:

```bash
make meeting-ready
```

Gera relatório em `artifacts/meeting-ready/<timestamp>/`:
- **Status:** MEETING_READY, READY_WITH_WARNINGS ou NOT_READY
- **Checklist:** Itens a verificar visualmente antes da reunião
- **URLs:** Todas as interfaces com links diretos
- **Comandos de emergência:** Restart, reset, logs
- **Roteiro:** Sugestão de apresentação de 30 minutos
- **Limitações:** PSP/PIX, dados fictícios, segurança

Validar o script:
```bash
make validate-meeting-ready
```

## Limitações e Fora de Escopo
- **PSP Real**: Não há integração com cartões ou PIX real nesta versão local.
- **Domínio Público**: O acesso é apenas via `localhost`.
- **HTTPS**: Embora o Caddy suporte, para demo local o HTTP é o padrão.
- **Escalabilidade**: Esta demo foca em uma única instância.

## Demonstração do CRM Local (Sales Ops)

O sistema inclui um CRM local para demonstrar a capacidade de estender o painel administrativo para operações de vendas.

1. **Popular Leads**: Execute `make sales-seed` para criar leads fictícios.
2. **Acessar Dashboard**: Vá para o Admin Dashboard.
3. **Gerenciar Leads**: Use a seção "Sales / Leads" para filtrar por status, adicionar novos contatos e avançar oportunidades no funil.
4. **Privacidade**: Note que nenhum dado de lead é enviado para serviços externos.
