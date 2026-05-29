---
owner: platform-ops
status: consolidated
---

# Governança de Artefatos

Este documento descreve as regras de limpeza e integridade para os artefatos gerados em cada release.

## Limpeza de Dados Sensíveis
O script `verify-release-artifacts.sh` garante que nenhum dado sensível vaze nos pacotes de release:
- **Proibido**: `.env`, chaves privadas (`.key`, `.pem`), bancos de dados locais (`data/*.db`), logs de produção.
- **Proibido**: Binários de modelos gigantes (devem ser baixados via registry) e caches de teste.

## Integridade (Checksums)
Cada release gera um arquivo `checksums.sha256` contendo o hash de todos os arquivos do pacote. Isso permite que o operador verifique se o download foi íntegro e não foi alterado.

## Verificação Manual
```bash
sha256sum -c checksums.sha256
```
