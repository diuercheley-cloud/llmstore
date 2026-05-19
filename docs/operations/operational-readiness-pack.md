# Operational Readiness Pack

Este pacote fornece ferramentas para validar se o `llm-inference-stack` está pronto para demonstrações, pilotos ou produção.

## Como Executar
Execute o comando abaixo na raiz do repositório:
```bash
make operational-readiness
```
Ou diretamente o script:
```bash
bash scripts/operational-readiness-pack.sh
```

## Artefatos Gerados
Os resultados são salvos em `artifacts/operational-readiness/latest/`:
- `summary.md`: Visão geral do status de prontidão.
- `checks.json`: Detalhamento técnico de todas as verificações.
- `recommendations.md`: Ações recomendadas para mitigar riscos ou falhas.

## Níveis de Status
- **demo_ready**: Sistema básico funcional (API, DB, Redis). Pode ter warnings (ex: sem GPU).
- **pilot_ready**: Tudo funcional, logs sanitizados, env ignorado pelo git.
- **needs_attention**: O sistema funciona, mas há riscos de segurança ou performance.
- **production_blocked**: Falhas críticas em infraestrutura ou banco de dados.

## Verificações Realizadas
1. **Infraestrutura**: Docker Compose, PostgreSQL, Redis.
2. **API**: Endpoints `/health`, `/ready`, `/metrics`.
3. **Segurança**: Arquivo `.env` (presença e se está no `.gitignore`).
4. **Hardware**: Detecção de GPU NVIDIA (best-effort).
5. **Configuração**: Modos de RBAC, PKI, Attestation e Tokenizer.
