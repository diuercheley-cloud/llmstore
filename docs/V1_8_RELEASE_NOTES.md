# v1.8.0 Hybrid AI Platform

## Resumo Executivo

A release `v1.8.0-hybrid-ai-platform` fecha a transição do projeto para uma plataforma híbrida capaz de operar em modo local-first, com suporte opcional a provedores cloud, roteamento inteligente, billing em BRL, wallet pré-paga, cache inteligente, RAG empresarial, administração híbrida e validação E2E consolidada.

O foco desta versão é ampliar capacidade operacional sem romper as premissas de segurança e previsibilidade do appliance local: providers cloud continuam desabilitados por padrão, PIX real permanece fora do escopo e PSP real permanece fora do escopo.

## O Que Mudou Desde v1.7.1

Desde `v1.7.1-post-release-polish`, a stack deixou de ser apenas um appliance local endurecido e passou a oferecer:

- orquestração multi-provider local/cloud com governança central;
- smart routing com políticas e fallback controlado;
- billing financeiro em BRL com custo, preço e margem;
- wallet pré-paga local/manual sem PSP nem PIX real;
- cache inteligente com impacto direto em custo e preço;
- RAG empresarial multi-tenant;
- admin híbrido com visão agregada;
- abuse detection com dry-run seguro;
- validação E2E híbrida e relatórios de readiness da plataforma.

## Multi-Provider

- Registry centralizado para provedores locais e cloud.
- Adapters configuráveis para capacidades, saúde, autenticação e status.
- Operação local-first com cloud providers desabilitados por padrão.
- Sanitização de health checks e configuração para não expor API keys nem detalhes sensíveis.

## Smart Routing

- Políticas de roteamento configuráveis por objetivo de negócio e perfil de workload.
- Estratégias para qualidade, custo, coding, local-first e fallback-only.
- Decisão de rota desacoplada dos endpoints de inferência.
- Fallback seguro entre provedores compatíveis, sem expor prompts ou secrets em logs e respostas administrativas.

## Billing BRL

- Motor de billing em BRL com custo, preço e margem por requisição.
- Regras por cliente para markup e visibilidade controlada.
- Câmbio manual/configurável, sem dependência de PSP nem consulta externa obrigatória.
- Integração com cache para refletir redução de custo em hits exatos/semânticos quando aplicável.

## Wallet Pré-Paga Local/Manual

- Carteira em BRL por cliente com saldo pré-pago.
- Crédito manual administrativo e débito automático por uso elegível.
- Idempotência transacional para evitar dupla cobrança.
- Sem PIX real e sem PSP real nesta release.

## Cache Inteligente

- Cache exato por fingerprint da requisição.
- Cache semântico opcional para reaproveitamento com similaridade.
- Isolamento multi-tenant e controles administrativos dedicados.
- Integração com billing, segurança e visibilidade operacional.

## RAG Empresarial

- Ingestão de documentos com pipeline empresarial de parse, chunking, embedding e retrieval.
- Estratégias de chunking voltadas a qualidade de contexto e governança.
- Isolamento por tenant, políticas de upload e verificações de segurança.
- Operação local compatível com testes sem necessidade de chamada cloud.

## Admin Híbrido

- APIs administrativas específicas para providers, routing, billing, wallet, cache, RAG e abuse detection.
- Dashboard/sumário híbrido com visão consolidada da plataforma.
- Separação clara entre dados internos de margem/custo e visibilidade do client portal.
- Sanitização obrigatória de credenciais e campos sensíveis.

## Abuse Detection

- Sinais de abuso correlacionados para identificar uso anômalo na plataforma híbrida.
- Modo dry-run como padrão seguro para observabilidade antes de enforcement.
- APIs administrativas para resumo, eventos e ações.
- Proteções para não expor critérios sensíveis nem impactar tenants legítimos por padrão.

## Limitações

- Cloud providers ficam disabled por padrão.
- PIX real continua fora do escopo.
- PSP real continua fora do escopo.
- Testes locais não devem executar chamadas cloud reais.

## Upgrade Path

1. Atualize o código para a branch/release `v1.8.0-hybrid-ai-platform`.
2. Revise variáveis e exemplos de configuração de providers, routing, pricing, wallet, cache e RAG.
3. Mantenha providers cloud desabilitados até validar credenciais, política de custo e governança.
4. Rode migrations e a suíte de validação híbrida local completa.
5. Revise os relatórios de Security Report e Production Readiness antes de promover a release.

## Status Esperado da Release

- Security Report: `PASS`
- Production Readiness: `READY` ou `READY_WITH_ACCEPTED_WARNINGS` documentado
- Cloud providers: disabled por padrão
- Sem versionar secrets, `.env`/`.local`, provider keys, `.gguf`, `data/rag_uploads`, artefatos brutos ou `.tar.gz`
