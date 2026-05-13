# Demo Storyboard — Local AI Appliance

## 1. Landing Page

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 1ª tela |
| **URL** | `http://localhost:18080/` |
| **Screenshot esperado** | Hero section com logo, título "Local AI Appliance", CTA para capabilities |
| **Fala sugerida** | "Este é o Local AI Appliance — um LLM-as-a-Service completo que roda 100% na sua infraestrutura. API compatível com OpenAI, RAG, TTS, billing manual. Nenhum dado sai da sua rede." |
| **Objetivo** | Apresentar o produto e propor valor |
| **Pontos de atenção** | Verificar se dados demo genéricos aparecem; sem tokens ou senhas na tela |

---

## 2. Capabilities Page

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 2ª tela |
| **URL** | `http://localhost:18080/capabilities` |
| **Screenshot esperado** | Tabela de capacidades com 18+ recursos, status e observações |
| **Fala sugerida** | "Transparência total: aqui listamos o que o sistema faz, o que é parcial e o que não está disponível. Veja que as limitações PSP/PIX e Tools/FC estão explícitas." |
| **Objetivo** | Demonstrar transparência sobre recursos e limitações |
| **Pontos de atenção** | Verificar se as limitações PSP/PIX real aparecem na página |

---

## 3. Admin Dashboard

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 3ª tela |
| **URL** | `http://localhost:18080/admin-dashboard` |
| **Screenshot esperado** | Visão geral com saúde dos serviços, consumo de tokens, clientes ativos |
| **Fala sugerida** | "Centro de comando do appliance: saúde dos serviços, consumo por cliente, latência e erros. Tudo on-premise, sem enviar métricas para SaaS externo." |
| **Objetivo** | Demonstrar monitoria completa local |
| **Pontos de atenção** | Usar dados demo; ADMIN_TOKEN não deve aparecer na URL ou no conteúdo |

---

## 4. Admin Lab — Modelos

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 4ª tela |
| **URL** | `http://localhost:18080/admin-lab` (aba Modelos) |
| **Screenshot esperado** | Lista de modelos com alias, arquivo GGUF, status, ações |
| **Fala sugerida** | "Gestão de modelos sem shell: ativar/desativar, testar prompt, trocar default, registrar backend externo — tudo pela interface." |
| **Objetivo** | Mostrar autonomia do administrador na gestão de modelos |
| **Pontos de atenção** | Verificar se não expõe caminhos absolutos do host |

---

## 5. Admin Lab — Financeiro

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 5ª tela |
| **URL** | `http://localhost:18080/admin-lab` (aba Faturas) |
| **Screenshot esperado** | Lista de invoices com status, valores, ações de marcar pago/cancelar |
| **Fala sugerida** | "Billing local/manual: invoices geradas por consumo. O administrador confirma pagamento manualmente. Não há PSP/PIX real integrado." |
| **Objetivo** | Mostrar ciclo de faturamento local |
| **Pontos de atenção** | Deixar claro que não há PSP/PIX real |

---

## 6. Client Portal

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 6ª tela |
| **URL** | `http://localhost:18080/client-portal` |
| **Screenshot esperado** | Dashboard do cliente com consumo, API keys, faturas |
| **Fala sugerida** | "Cada cliente acessa seu portal. Vê consumo, gera/rotaciona chaves, consulta faturas. Isolamento total entre tenants." |
| **Objetivo** | Demonstrar autoatendimento do cliente com isolamento |
| **Pontos de atenção** | Usar API key demo; ADMIN_TOKEN não deve estar presente |

---

## 7. API OpenAI-compatible

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 7ª tela |
| **URL** | `POST http://localhost:18080/v1/chat/completions` |
| **Screenshot esperado** | Terminal com curl mostrando request e resposta JSON |
| **Fala sugerida** | "API 100% compatível com OpenAI. Qualquer SDK que use OpenAI funciona trocando apenas a base_url. A inferência roda no modelo local GGUF." |
| **Objetivo** | Demonstrar compatibilidade com ecossistema OpenAI |
| **Pontos de atenção** | API_KEY deve ser demo; não expor key real |

---

## 8. RAG Demo

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 8ª tela |
| **URL** | `POST http://localhost:18080/v1/rag/query` |
| **Screenshot esperado** | Requisição RAG com pergunta e resposta com contexto |
| **Fala sugerida** | "Documentos internos são indexados localmente. O modelo busca o contexto relevante e responde com base nos documentos. Dados jamais saem da infraestrutura." |
| **Objetivo** | Demonstrar Retrieval-Augmented Generation local |
| **Pontos de atenção** | Documentos devem ser fictícios (demo) |

---

## 9. TTS Demo

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 9ª tela |
| **URL** | `POST http://localhost:18080/pocket-tts/tts` |
| **Screenshot esperado** | Terminal com requisição TTS e confirmação de áudio gerado |
| **Fala sugerida** | "Geração de áudio 100% local — sem enviar texto para serviços cloud. Útil para call centers, IVR e acessibilidade." |
| **Objetivo** | Demonstrar Text-to-Speech local |
| **Pontos de atenção** | Verificar se pocket-tts está habilitado e funcionando |

---

## 10. Sales / Leads

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 10ª tela |
| **URL** | `http://localhost:18080/admin-dashboard#sales` |
| **Screenshot esperado** | Pipeline de vendas com leads em diferentes estágios |
| **Fala sugerida** | "CRM integrado: pipeline de vendas com leads, estágios e notas. Tudo local — nem dados de prospecção saem da sua rede." |
| **Objetivo** | Mostrar gestão comercial integrada |
| **Pontos de atenção** | Leads devem ser fictícios (demo seed) |

---

## 11. Pricing / Plans

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 11ª tela |
| **URL** | `http://localhost:18080/pricing` |
| **Screenshot esperado** | Tabela de planos (Free, Basic, Pro, Enterprise) com limites |
| **Fala sugerida** | "Planos pré-configurados: Free para testes, Basic para projetos, Pro para produção e Enterprise Local para alto volume." |
| **Objetivo** | Demonstrar modelo de precificação |
| **Pontos de atenção** | Preços são ilustrativos; verificar se não há dados reais |

---

## 12. Security Report

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 12ª tela |
| **Comando** | `./scripts/security-report-local.sh` |
| **Screenshot esperado** | Output do relatório de segurança com itens verificados |
| **Fala sugerida** | "Relatório automatizado de segurança: varre secrets, permissões, portas. Use como insumo para compliance — não substitui auditoria formal." |
| **Objetivo** | Demonstrar compromisso com segurança |
| **Pontos de atenção** | Relatório não deve expor secrets reais |

---

## 13. Production Readiness

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 13ª tela |
| **Comando** | `./scripts/production-readiness-local.sh` |
| **Screenshot esperado** | Output do readiness check com status por item |
| **Fala sugerida** | "Checklist de prontidão: conectividade, GPU, modelos, CORS, backup, isolamento multi-tenant. Cada item com status claro." |
| **Objetivo** | Demonstrar prontidão para produção |
| **Pontos de atenção** | Verificar se todos os serviços estão rodando |

---

## 14. Meeting Ready Report

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 14ª tela |
| **Comando** | `make meeting-ready` |
| **Screenshot esperado** | Relatório meeting-ready com status, checklist, URLs |
| **Fala sugerida** | "Antes de cada reunião com cliente, rodamos este check que valida se está tudo pronto para a apresentação." |
| **Objetivo** | Demonstrar preparação para reuniões com clientes |
| **Pontos de atenção** | Verificar se o relatório está completo |

---

## 15. Proposal / Quote / SOW Output

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 15ª tela |
| **Comando** | `make generate-proposal COMPANY_NAME="Cliente Demo"` |
| **Screenshot esperado** | Proposta técnica ou comercial gerada |
| **Fala sugerida** | "Proposta personalizada gerada em segundos. Pronta para revisão e envio ao cliente." |
| **Objetivo** | Demonstrar agilidade na geração de propostas |
| **Pontos de atenção** | Proposta deve usar nome demo; sem dados reais de clientes |

---

## Resumo do Fluxo

| # | Tela | Tipo | URL/Comando | Duração |
|---|------|------|-------------|---------|
| 1 | Landing Page | Web | `/` | 1 min |
| 2 | Capabilities | Web | `/capabilities` | 2 min |
| 3 | Admin Dashboard | Web | `/admin-dashboard` | 4 min |
| 4 | Admin Lab — Modelos | Web | `/admin-lab` | 2 min |
| 5 | Admin Lab — Financeiro | Web | `/admin-lab#faturas` | 2 min |
| 6 | Client Portal | Web | `/client-portal` | 3 min |
| 7 | API Examples | Terminal | `/v1/chat/completions` | 3 min |
| 8 | RAG Demo | Terminal | `/v1/rag/query` | 3 min |
| 9 | TTS Demo | Terminal | `/pocket-tts/tts` | 2 min |
| 10 | Sales/Leads | Web | `/admin-dashboard#sales` | 2 min |
| 11 | Pricing/Plans | Web | `/pricing` | 2 min |
| 12 | Security Report | Terminal | `scripts/security-report-local.sh` | 2 min |
| 13 | Production Readiness | Terminal | `scripts/production-readiness-local.sh` | 2 min |
| 14 | Meeting Ready | Terminal | `make meeting-ready` | 1 min |
| 15 | Proposal/Quote/SOW | Terminal | `make generate-proposal` | 2 min |

## 16. System Control Center (se disponível)

| Campo | Detalhe |
|-------|---------|
| **Ordem** | 16ª tela (opcional) |
| **URL** | `http://localhost:18080/system-control-center` (se existir) |
| **Screenshot esperado** | Painel centralizado com status de todos os componentes |
| **Fala sugerida** | "Centro de controle do sistema: visão consolidada de todos os serviços e dependências." |
| **Objetivo** | Demonstrar visão consolidada do sistema |
| **Pontos de atenção** | Pode não estar disponível em todas as instalações
