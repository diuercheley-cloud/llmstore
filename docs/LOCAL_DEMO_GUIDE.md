# Guia de Demonstração Local - llm-inference-stack

Este guia descreve como preparar e executar uma demonstração completa do produto em um ambiente local (como um notebook com WSL2), sem dependência de nuvem, domínios públicos ou gateways de pagamento reais.

## Objetivo da Demo
Demonstrar a soberania de dados, facilidade de implantação, portal do cliente, governança de API e billing manual, tudo rodando localmente com aceleração de GPU (quando disponível).

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

## Limitações e Fora de Escopo
- **PSP Real**: Não há integração com cartões ou PIX real nesta versão local.
- **Domínio Público**: O acesso é apenas via `localhost`.
- **HTTPS**: Embora o Caddy suporte, para demo local o HTTP é o padrão.
- **Escalabilidade**: Esta demo foca em uma única instância.
