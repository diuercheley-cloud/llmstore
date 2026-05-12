# v1.7.0 Local AI Appliance

## Resumo Executivo
A versão v1.7.0 consolida todo o trabalho da linha v1.6.x, entregando o **Local AI Appliance**. Esta release transforma o projeto de um conjunto de ferramentas e APIs em um produto empacotado, pronto para implantação local com fluxos comerciais, de administração e operação totalmente funcionais em ambiente on-premise ou isolado. 

## O que é o Local AI Appliance
O Local AI Appliance é uma solução completa de Inteligência Artificial para implantação local ("air-gapped" ou "on-premise"). Ele empacota modelos, RAG, TTS, painéis administrativos e portais de cliente em uma única entrega focada em privacidade de dados, sem dependência de APIs externas de cloud para inferência. É projetado para vendas B2B, com white-label básico e geração de propostas e contratos embarcados.

## Principais Recursos Consolidados
Esta versão inclui a estabilização e integração final dos seguintes recursos:
- **OpenAI-compatible API:** APIs de embeddings e chat completions compatíveis com o ecossistema OpenAI.
- **RAG Multi-tenant:** Geração aumentada por recuperação com isolamento de dados entre tenants.
- **TTS Local:** Text-to-Speech integrado e processado localmente.
- **Embeddings/Responses:** Processamento local de vetores e respostas.
- **Admin Dashboard / Admin Lab:** Painel de controle para gerenciar a instância, testar modelos e verificar saúde do sistema.
- **Client Portal:** Portal do cliente com CRM básico e faturamento.
- **Billing Local/Manual:** Geração de orçamentos e relatórios manuais/locais de faturamento.
- **Security/Readiness Reports:** Relatórios automáticos de prontidão e segurança, garantindo a conformidade da instalação.
- **Installer / Wizard:** Instalador aprimorado com assistente de configuração local.
- **Demo Pack:** Conjunto de demonstrações comerciais (cenários, PDFs, scripts).
- **Sales Ops:** Fluxos de CRM, geração de propostas, SOW, checklist de implantação e relatórios mensais.
- **White-label Básico:** Configuração de branding local.
- **Backup/Restore/Rollback:** Fluxos completos e validados de proteção de dados e atualizações.

## Linha do Tempo v1.6.x
A linha v1.6.x preparou o terreno iterativamente para esta consolidação:
- **v1.6.0:** OpenAI-compatible responses e embeddings APIs.
- **v1.6.1:** Product hardening (System control center, migrations, multi-tenant).
- **v1.6.2:** Installer polish (Instalador local, wizard, backup/upgrade).
- **v1.6.3:** Readiness cleanup (Probe chat/SSE/TTS/CORS, status final de prontidão).
- **v1.6.4:** Customer demo pack (5 cenários comerciais, capabilities).
- **v1.6.5:** Sales ops (CRM, propostas, orçamentos, contratos, white-label).
- **v1.6.6:** Repo cleanup (Consolidação de layout, padronização shell).
- **v1.6.7:** Final QA (Relatórios de prontidão, checklists de promoção e auditoria geral).

## Limitações
- **PSP Real Fora do Escopo:** Integração real com Provedores de Serviço de Pagamento (ex: Stripe) não está incluída.
- **PIX Real Fora do Escopo:** Pagamentos reais via PIX não estão habilitados.
- **Cloud Gerenciada Fora do Escopo:** A solução é estritamente local; não há plano de controle em cloud gerenciado.
- **Desempenho:** O desempenho do sistema depende inteiramente do hardware local e do modelo LLM implantado.
- **Function Calling / Tools:** Suporte parcial ou reservado para futuras iterações (future).

## Critérios de Aceite
- Todos os serviços principais iniciam corretamente em ambiente isolado.
- APIs de Chat e Embeddings respondem no formato compatível com OpenAI.
- Geração de propostas comerciais e contratos funciona sem requerer secrets reais.
- Testes E2E de demo comercial, restore/rollback e clean install passam sem erros críticos.
- Relatório Client Ready Final gerado com status Go.

## Upgrade Path a partir de v1.6.x
1. Execute o script de backup da versão atual (`scripts/backup-local.sh`).
2. Utilize o script de upgrade validado (`scripts/upgrade-rollback-local.sh`) apontando para o bundle da v1.7.0.
3. Valide o status dos serviços via Admin Lab ou scripts de prontidão.
4. Em caso de falha, execute o rollback usando o snapshot criado no passo 1.

## Release Bundle

A release v1.7.0-local-ai-appliance inclui um bundle de release versionado em:

```
releases/v1.7.0-local-ai-appliance/
  release-manifest.json   - Metadados da release (git, validacao, inclusoes)
  summary.json            - Resumo da validacao de producao local
  summary.md              - Resumo em formato markdown
  bundle-manifest.json    - Manifesto do bundle de distribuicao (tar.gz)
  bundle-checksums.sha256 - Checksums SHA256 do arquivo .tar.gz
```

O arquivo `.tar.gz` (distribuivel) é gerado mas **não versionado** no git.
Apenas os manifests e checksums seguros são versionados.

### Bundle seguro

- Secrets scan obrigatório durante a criação do bundle.
- Nenhum `.env`, `.env.local`, `.local`, `models/*.gguf`, `data/rag_uploads`, `backups`, `exports` ou `artifacts` são incluídos.
- Security validation executada contra o diretório de release.
- `validate-release-artifacts-security.sh` garante que nenhum `.tar.gz` está trackeado no git.

## Validacao Final

A validacao final da v1.7.0 é executada por:

```bash
./scripts/validate-v1.7-final-local.sh           # Orquestrador completo
./scripts/validate-v1.7-final-report.sh           # Valida o relatorio gerado
```

O relatório consolidado fica em:

```
artifacts/v1.7-final-validation/<timestamp>/
  v1.7-final-validation.json  - Relatorio em JSON
  v1.7-final-validation.md    - Relatorio em Markdown
  logs/                       - Logs de cada validacao
```

### Status final

| Status | Significado |
|--------|-------------|
| V1_7_READY | Todas as validacoes PASS |
| V1_7_READY_WITH_WARNINGS | Warnings nao bloqueantes documentados |
| V1_7_NOT_READY | Blocker detectado |

### Validações executadas

1. check-secrets --all
2. security-report-local.sh
3. production-readiness-local.sh
4. validate-local-production-full.sh
5. validate-clean-install-local.sh --dry-run
6. validate-commercial-demo-e2e-local.sh --seed-demo
7. validate-client-ready-report.sh
8. validate-release-artifacts-security.sh
9. validate-v1.7-release-bundle.sh
10. run-v1.7-release-checklist.sh
11. Validate release metadata (manifests, version, checksums)

## Próximos Passos Pós-v1.7.0
- Monitoramento de deployments reais (Early Access).
- Correção de bugs de pós-lançamento via patches (v1.7.1, etc).
- Planejamento de suporte completo a function calling e integrações externas (caso escopo seja expandido).
