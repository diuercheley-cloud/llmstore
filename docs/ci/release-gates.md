---
owner: platform-ops
status: consolidated
---

# Release Gates

Para atingir o estado "Ready for Release", os seguintes critérios devem ser satisfeitos:

1. **Estabilidade**: Zero falhas em testes de fumaça (Smoke).
2. **Resiliência**: Sobrevivência a testes de caos controlados.
3. **Readiness**: 100% de sucesso no `operational-readiness-pack.sh`.
4. **Segurança**: Scan de CVEs limpo para dependências de produção.
