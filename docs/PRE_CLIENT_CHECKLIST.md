# Pre-Client / Pre-Demo Checklist

Este documento descreve o processo de validação automatizada antes de realizar uma demonstração para clientes ou instalar o sistema em um ambiente de produção local.

## Objetivo
Garantir que todos os componentes críticos estejam operacionais, seguros e seguindo as melhores práticas antes da exposição ao cliente.

## Validacao E2E da Demo Comercial

Para uma validacao completa do fluxo de demonstracao comercial (seed, meeting-ready, APIs, propostas, orcamentos, SOW, relatorios):

```bash
./scripts/validate-commercial-demo-e2e-local.sh --seed-demo
```

Relatorio gerado em `artifacts/final-qa/commercial-demo-e2e/<timestamp>/` com status `DEMO_READY`, `DEMO_READY_WITH_WARNINGS` ou `DEMO_FAILED`.

## Como Executar

### Para Demonstração
Gera um checklist focado em cenários de demo, incluindo validação de dados de exemplo.
```bash
make pre-demo-check
# Ou diretamente:
./scripts/pre-client-checklist-local.sh --demo
```

### Para Instalação em Cliente
Gera um checklist focado em prontidão de produção e segurança.
```bash
make pre-client-check
# Ou diretamente:
./scripts/pre-client-checklist-local.sh --client-install
```

## Opções Disponíveis
- `--strict`: Falha (NO_GO) se houver qualquer aviso (WARNING).
- `--base-url`: Especifica a URL base do stack (padrão: http://localhost:18080).
- `--skip-rag` / `--skip-tts`: Pula validações específicas se os componentes não forem usados.

## Componentes Validados
- Saúde dos Containers Docker
- Endpoints de API (/health, /ready, /status)
- Segurança (Secrets, Security Report)
- Prontidão de Produção (Readiness Report)
- Isolamento Multitenant e Proteção contra Abuso
- Planos Comerciais e Billing Local
- RAG, TTS e LM Studio (se habilitados)
- Embeddings API e Responses API
- Artefatos de Release e Metadados

## Relatórios Gerados
Os relatórios são salvos em `artifacts/pre-client-checklists/<timestamp>/`:
- `checklist.json`: Dados estruturados para integração.
- `checklist.md`: Relatório formatado para leitura humana.
- `logs/`: Logs detalhados de cada check individual.

## Critérios de Status
- **GO**: Tudo passou perfeitamente.
- **GO_WITH_WARNINGS**: Sistema funcional, mas existem pendências menores (ex: git dirty).
- **NO_GO**: Falhas críticas (ex: containers baixos, endpoints inacessíveis, segredos expostos).

## Reset de Dados Demo (Antes/Depois de Reuniões)

Para garantir que dados de demonstração sejam removidos com segurança antes ou depois de reuniões com clientes:

```bash
# Validar seguranca do reset
make validate-reset-demo-pack

# Simular reset (nao apaga nada)
make reset-demo-pack

# Reset real apos confirmacao
./scripts/reset-commercial-demo-pack.sh --yes

# Reset completo com todos os dados demo
./scripts/reset-commercial-demo-pack.sh --yes --include-rag --include-tts --include-invoices --include-usage
```

**Segurança:** O reset usa `metadata demo=true` para identificar dados demo, nunca afetando dados reais de clientes.

## Meeting Ready Check (Pré-Reunião com Cliente)

Para uma verificação focada especificamente em apresentações ao cliente, incluindo roteiro e URLs:

```bash
make meeting-ready
# Ou diretamente:
./scripts/meeting-ready-check-local.sh
```

Gera relatório em `artifacts/meeting-ready/<timestamp>/` com:
- Status MEETING_READY, READY_WITH_WARNINGS ou NOT_READY
- Checklist visual prático
- Roteiro de apresentação de 30 minutos sugerido
- URLs e comandos de emergência
- Limitações a mencionar (PSP/PIX, dados fictícios)

```bash
# Validar o script de meeting-ready
make validate-meeting-ready
```

## Próximos Passos
Após gerar o relatório:
1. Revise o `checklist.md` ou `meeting-ready.md`.
2. Se `NO_GO` ou `NOT_READY`, resolva os erros listados nos logs.
3. Se `GO_WITH_WARNINGS` ou `READY_WITH_WARNINGS`, avalie se os riscos são aceitáveis para o cenário atual.
4. Anexe o relatório ao processo de entrega/apresentação.
