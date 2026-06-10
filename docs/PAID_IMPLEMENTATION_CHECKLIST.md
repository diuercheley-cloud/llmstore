---
owner: platform-ops
status: consolidated
---

# Paid Implementation Checklist — Local AI Appliance

> **AVISO:** Este checklist é uma ferramenta operacional para implantação do LLM Inference Stack em modo Local Appliance. Não substitui o SOW, contrato de prestação de serviços ou assessoria jurídica. Não processa pagamentos reais via PSP/PIX — o módulo de faturamento opera exclusivamente em modo simulado/local.

**Empresa / Cliente:** ___________________________________________________  
**Operador / Fornecedor:** ________________________________________________  
**Data de início:** __________________ **Data prevista de conclusão:** __________________  
**Plano contratado:** ¨ Basic   ¨ Pro   ¨ Enterprise Local  
**Versão do software:** __________________  

---

## Instruções de Preenchimento

- Cada item deve receber um status conforme abaixo.
- Itens com status `BLOCKED` devem ter o motivo registrado no campo **Observações**.
- O checklist deve ser preenchido pelo operador do fornecedor e validado pelo cliente na etapa de aceite.
- **Não incluir senhas, tokens ou dados sensíveis neste documento.** Use referências a cofres de senhas.

### Status

| Status | Significado |
|--------|-------------|
| `NOT_STARTED` | Atividade ainda não iniciada |
| `IN_PROGRESS` | Atividade em andamento |
| `BLOCKED` | Atividade bloqueada (registrar motivo) |
| `READY_FOR_ACCEPTANCE` | Atividade concluída, aguardando validação do cliente |
| `ACCEPTED` | Atividade concluída e aceita pelo cliente |

---

## 1. Antes da Implantação

| # | Atividade | Responsável | Status | Observações |
|---|-----------|-------------|--------|-------------|
| 1.1 | Contrato/SOW assinado por ambas as partes | Fornecedor / Cliente | | |
| 1.2 | Template de contrato revisado por assessoria jurídica | Fornecedor | | |
| 1.3 | Plano e módulos contratados confirmados (RAG, TTS, etc.) | Fornecedor / Cliente | | |
| 1.4 | Escopo e cronograma acordados | Fornecedor / Cliente | | |
| 1.5 | Ponto focal técnico do cliente designado | Cliente | | |
| 1.6 | Acesso ao ambiente do cliente liberado (VPN/SSH/remoto) | Cliente | | |
| 1.7 | Checklist de requisitos de hardware enviado ao cliente | Fornecedor | | |
| 1.8 | Reunião de kickoff realizada | Fornecedor / Cliente | | |

## 2. Requisitos de Hardware

| # | Atividade | Responsável | Status | Observações |
|---|-----------|-------------|--------|-------------|
| 2.1 | Sistema operacional Ubuntu 22.04 LTS+ instalado e atualizado | Cliente | | |
| 2.2 | Docker Engine 24+ e Docker Compose V2 instalados | Cliente | | |
| 2.3 | CPU 8+ cores x86_64 com suporte a AVX2 | Cliente | | |
| 2.4 | RAM mínima confirmada (32 GB Basic / 64 GB Pro/Enterprise) | Cliente | | |
| 2.5 | SSD NVMe com espaço suficiente (100 GB + modelos) | Cliente | | |
| 2.6 | GPU NVIDIA com 8 GB+ VRAM e drivers CUDA 12.x (se aplicável) | Cliente | | |
| 2.7 | Acesso à internet para download inicial de imagens e modelos | Cliente | | |
| 2.8 | Portas necessárias liberadas no firewall | Cliente | | |

## 3. Requisitos de Acesso

| # | Atividade | Responsável | Status | Observações |
|---|-----------|-------------|--------|-------------|
| 3.1 | Acesso SSH ou console ao servidor liberado | Cliente | | |
| 3.2 | Usuário com permissão sudo ou docker para o operador | Cliente | | |
| 3.3 | Acesso ao repositório ou pacote de instalação liberado | Fornecedor | | |
| 3.4 | Credenciais de acesso fornecidas de forma segura (fora deste doc) | Cliente / Fornecedor | | |
| 3.5 | Conexão de rede estável verificada | Cliente | | |
| 3.6 | Acesso à interface administrativa testado (`http://localhost:18080/admin`) | Fornecedor | | |

## 4. Responsabilidades do Cliente

| # | Atividade | Status | Observações |
|---|-----------|--------|-------------|
| 4.1 | Disponibilizar infraestrutura conforme requisitos de hardware | | |
| 4.2 | Manter SO e Docker atualizados | | |
| 4.3 | Garantir backup dos dados existentes antes da implantação | | |
| 4.4 | Designar equipe técnica para acompanhamento e treinamento | | |
| 4.5 | Obter licenças necessárias para modelos proprietários ou dados de terceiros | | |
| 4.6 | Não modificar a configuração do ambiente sem consultar o fornecedor | | |
| 4.7 | Manter política de segurança da informação (firewall, antivírus, etc.) | | |

## 5. Responsabilidades do Fornecedor

| # | Atividade | Status | Observações |
|---|-----------|--------|-------------|
| 5.1 | Entregar software em condições de funcionamento conforme especificação | | |
| 5.2 | Realizar implantação dentro do cronograma acordado | | |
| 5.3 | Utilizar credenciais temporárias durante a implantação | | |
| 5.4 | Não extrair, copiar ou reter dados do cliente | | |
| 5.5 | Fornecer documentação de operação e manutenção | | |
| 5.6 | Realizar treinamento da equipe do cliente | | |
| 5.7 | Corrigir falhas comprovadas dentro do SLA contratado | | |

## 6. Backup Inicial

| # | Atividade | Responsável | Status | Observações |
|---|-----------|-------------|--------|-------------|
| 6.1 | Backup dos dados existentes do cliente realizado antes da instalação | Cliente | | |
| 6.2 | Backup da configuração inicial ao final da implantação | Fornecedor | | |
| 6.3 | Script `scripts/backup/backup-local.sh` testado e funcional | Fornecedor | | |
| 6.4 | Backup armazenado em local seguro e fora do ambiente principal | Cliente | | |
| 6.5 | Procedimento de restore verificado | Fornecedor | | |

## 7. Instalação

| # | Atividade | Responsável | Status | Observações |
|---|-----------|-------------|--------|-------------|
| 7.1 | Repositório clonado / pacote extraído no servidor | Fornecedor | | |
| 7.2 | Arquivo `.env.local` configurado com credenciais seguras | Fornecedor | | |
| 7.3 | Stack inicializada (`./scripts/deploy/install-local-appliance.sh`) | Fornecedor | | |
| 7.4 | Todos os containers healthy (`docker compose ps`) | Fornecedor | | |
| 7.5 | Migrações de banco de dados executadas sem erros | Fornecedor | | |
| 7.6 | Logs verificados sem erros críticos | Fornecedor | | |

## 8. Configuração

| # | Atividade | Responsável | Status | Observações |
|---|-----------|-------------|--------|-------------|
| 8.1 | Wizard de configuração executado (`./scripts/dev/configure-local-wizard.sh`) | Fornecedor | | |
| 8.2 | Planos comerciais seedados e validados | Fornecedor | | |
| 8.3 | Clientes/tenants criados conforme necessidade do cliente | Fornecedor | | |
| 8.4 | Tokens de API gerados e entregues de forma segura | Fornecedor | | |
| 8.5 | Multi-tenancy configurado e validado | Fornecedor | | |
| 8.6 | CORS configurado para o ambiente local do cliente | Fornecedor | | |

## 9. Modelos

| # | Atividade | Responsável | Status | Observações |
|---|-----------|-------------|--------|-------------|
| 9.1 | Modelos GGUF copiados para `models/` | Fornecedor / Cliente | | |
| 9.2 | Modelo padrão configurado e carregado | Fornecedor | | |
| 9.3 | Inferência testada com modelo carregado | Fornecedor | | |
| 9.4 | Benchmark de performance executado | Fornecedor | | |

## 10. Segurança

| # | Atividade | Responsável | Status | Observações |
|---|-----------|-------------|--------|-------------|
| 10.1 | Senhas e tokens do .env.local são fortes e únicos | Fornecedor | | |
| 10.2 | `ADMIN_TOKEN` e `JWT_SECRET` alterados (não valores padrão) | Fornecedor | | |
| 10.3 | Verificação de secrets no código (`make check-secrets`) | Fornecedor | | |
| 10.4 | Relatório de segurança gerado (`make security`) | Fornecedor | | |
| 10.5 | Firewall do servidor verificado (portas mínimas expostas) | Cliente | | |
| 10.6 | Proteção contra abuso validada (`make validate-abuse`) | Fornecedor | | |
| 10.7 | Acesso root/administrador removido ou desabilitado | Cliente | | |

## 11. Testes de Aceite

| # | Atividade | Responsável | Status | Observações |
|---|-----------|-------------|--------|-------------|
| 11.1 | Health check (`/health`) retorna HTTP 200 | Fornecedor | | |
| 11.2 | Readiness (`/ready`) retorna HTTP 200 | Fornecedor | | |
| 11.3 | Inferência funcional (`/v1/chat/completions`) | Fornecedor | | |
| 11.4 | Módulos contratados ativos e funcionais (RAG, TTS, etc.) | Fornecedor | | |
| 11.5 | Isolamento multi-tenant verificado | Fornecedor | | |
| 11.6 | Validação pós-instalação executada (`make validate-post-install`) | Fornecedor | | |
| 11.7 | Validação completa de produção executada (`make validate`) | Fornecedor | | |
| 11.8 | Testes de carga básicos executados (se aplicável) | Fornecedor | | |

## 12. Treinamento do Operador

| # | Atividade | Responsável | Status | Observações |
|---|-----------|-------------|--------|-------------|
| 12.1 | Sessão de transferência de conhecimento realizada | Fornecedor | | |
| 12.2 | Equipe do cliente treinada em operações básicas (start/stop/logs) | Fornecedor | | |
| 12.3 | Equipe do cliente treinada em backup e restore | Fornecedor | | |
| 12.4 | Equipe do cliente treinada em criação de clientes/API keys | Fornecedor | | |
| 12.5 | Guia de operação entregue e revisado com a equipe | Fornecedor | | |
| 12.6 | Canais de suporte apresentados à equipe do cliente | Fornecedor | | |

## 13. Entrega Final

| # | Atividade | Responsável | Observações |
|---|-----------|-------------|-------------|
| 13.1 | Todos os itens do checklist com status `ACCEPTED` ou justificados | Fornecedor / Cliente | |
| 13.2 | Termo de aceite assinado pelo cliente | Cliente | |
| 13.3 | Documentação final entregue | Fornecedor | |
| 13.4 | Credenciais e tokens entregues de forma segura | Fornecedor | |
| 13.5 | Ambiente de produção liberado para uso do cliente | Fornecedor | |

## 14. Pós-Implantação

| # | Atividade | Responsável | Status | Observações |
|---|-----------|-------------|--------|-------------|
| 14.1 | Monitoramento inicial do ambiente (primeiros dias) | Fornecedor | | |
| 14.2 | Validação de logs e métricas após uso real | Fornecedor | | |
| 14.3 | Ajustes finos de performance conforme necessidade | Fornecedor | | |
| 14.4 | Reunião de pós-implantação agendada (NPS / feedback) | Fornecedor / Cliente | | |
| 14.5 | Chamado de suporte aberto para acompanhamento contínuo | Fornecedor | | |

## 15. Assinaturas / Check Final

| Item | Descrição | Assinatura / Validação |
|------|-----------|------------------------|
| A | Declaro que o sistema foi implantado conforme o escopo acordado e todos os itens aplicáveis foram verificados. | **Operador (Fornecedor):** ________________________ Data: ________ |
| B | Declaro que recebi o sistema em condições de uso, conforme critérios de aceite, e autorizo a liberação do ambiente. | **Cliente:** ______________________________________ Data: ________ |
| C | **PSP/PIX:** Confirmo que fui informado de que **não há processamento de pagamentos reais via PSP ou PIX** nesta versão do sistema. O módulo de faturamento é simulado/local. | **Cliente:** ______________________________________ Data: ________ |
| D | **Dados sensíveis:** Nenhuma senha, token ou informação confidencial foi registrada neste documento. | **Operador:** _____________________________________ Data: ________ |

---

## Resumo de Status

| Seção | Total Itens | NOT_STARTED | IN_PROGRESS | BLOCKED | READY_FOR_ACCEPTANCE | ACCEPTED |
|-------|-------------|-------------|-------------|---------|----------------------|----------|
| 1. Antes da Implantação | | | | | | |
| 2. Requisitos de Hardware | | | | | | |
| 3. Requisitos de Acesso | | | | | | |
| 4. Responsab. do Cliente | | | | | | |
| 5. Responsab. do Fornecedor | | | | | | |
| 6. Backup Inicial | | | | | | |
| 7. Instalação | | | | | | |
| 8. Configuração | | | | | | |
| 9. Modelos | | | | | | |
| 10. Segurança | | | | | | |
| 11. Testes de Aceite | | | | | | |
| 12. Treinamento | | | | | | |
| 14. Pós-Implantação | | | | | | |
| **Total** | **___** | **___** | **___** | **___** | **___** | **___** |

---

*Template v1.0 — LLM Inference Stack — Paid Implementation Checklist — Gerado em {{DATE}}*
