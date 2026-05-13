# V1.7.1 Warning Cleanup Report

Este documento detalha o processo de diagnóstico e limpeza de warnings não bloqueantes após a release v1.7.0.

## Resumo Executivo

| Métrica | Inicial (v1.7.0) | Atual (v1.7.1) |
|---------|-----------------|---------------|
| Status Final | V1_7_READY_WITH_WARNINGS | V1_7_READY_WITH_ACCEPTED_WARNINGS |
| Warnings Fixable | 7 | 0 |
| Warnings Aceitos | 4 | 4 |

## Warnings Corrigidos

| Item | Causa Raiz | Correção Aplicada |
|------|------------|-------------------|
| VERSION atualizada | Script de checklist esperava v1.7.0 exato. | Ajustado para aceitar padrão `v1.7.x`. |
| Branch correta | Script não aceitava branches de polish `feature/v1.7.1-*`. | Ajustado para aceitar `feature/v1.7.*`. |
| Release manifest OK | Verificação era um placeholder PENDENTE. | Implementada verificação real do arquivo no diretório de release. |
| Chat/Responses/Embeddings 405 | Uso de GET em endpoints que requerem POST. | Atualizado script de validação para usar `POST`. |
| Fake data / Demo pack failures | Falso positivo por grep no termo "FAIL: 0". | Atualizado para validar via exit code dos scripts. |

## Warnings Aceitos (Accepted Non-Blocking)

| Item | Motivo do Aceite | Classificação |
|------|------------------|---------------|
| PSP/PIX real fora do escopo | Pagamento real não é requisito para appliance local. | `accepted_non_blocking` |
| RAG 404 | Serviço de RAG é opcional e depende do ambiente (data plane). | `environment_specific` |
| TTS 404 | Serviço de TTS (pocket-tts) é opcional e pode estar offline. | `optional_dependency` |
| Meeting-ready warnings | Dependências opcionais (RAG/TTS) geram warnings no status. | `accepted_non_blocking` |

## Status Final

O sistema está **V1_7_READY**. Todos os bloqueadores estão resolvidos e os warnings restantes foram auditados e aceitos conforme a política de release.

---
*Gerado em: 2026-05-12*
