# Release Artifacts Management

Este repositório mantém apenas os artefatos da versão mais recente em `releases/latest/`. Todos os artefatos históricos (bundles, manifests, checksums) são movidos para o **GitHub Releases** para reduzir o peso do repositório Git.

## Onde encontrar releases antigos

Todos os artefatos de versões anteriores podem ser encontrados na aba [Releases](https://github.com/kleber/llm-inference-stack/releases) do GitHub.

Para baixar artefatos de uma versão específica via CLI:

```bash
gh release download <v_tag> --dir ./downloads
```

## Estrutura Atual

- `releases/latest/`: Contém os manifests e sumários da versão estável mais recente.
- **GitHub Releases**: Contém o histórico completo de bundles e binários.

## Automação de Publicação

O pipeline de CI (`.github/workflows/release.yml`) está configurado para:
1. Validar a qualidade da release.
2. Criar uma nova release no GitHub quando uma tag `v*` é disparada.
3. Subir automaticamente os artefatos gerados para a release do GitHub usando o script `scripts/release/upload_release_artifacts.sh`.

## Como subir artefatos manualmente

Caso necessário, você pode usar o script de upload:

```bash
# Requer gh CLI autenticado
./scripts/release/upload_release_artifacts.sh <v_tag> <diretorio_de_artefatos>
```
