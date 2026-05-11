# Pre-Client / Pre-Demo Checklist

Este documento descreve o processo de validação automatizada antes de realizar uma demonstração para clientes ou instalar o sistema em um ambiente de produção local.

## Objetivo
Garantir que todos os componentes críticos estejam operacionais, seguros e seguindo as melhores práticas antes da exposição ao cliente.

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

## Próximos Passos
Após gerar o relatório:
1. Revise o `checklist.md`.
2. Se `NO_GO`, resolva os erros listados nos logs.
3. Se `GO_WITH_WARNINGS`, avalie se os riscos são aceitáveis para o cenário atual.
4. Anexe o relatório ao processo de entrega/apresentação.
