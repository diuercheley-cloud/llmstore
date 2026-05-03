# Checkpoint Estável - 2026-05-03

## Status
- DR sem Bonsai: OK
- DR com Bonsai: OK
- validate-system-health --full: OK
- pytest: OK
- UI health: OK

## Correções incluídas
- fix dr-test.sh:
  - isolamento de COMPOSE_PROJECT_NAME
  - mktemp para arquivos temporários
  - logs detalhados em falha
  - flag --include-bonsai

## Observações
- corrida paralela resolvida com mktemp
- ambiente principal não afetado

## Comandos validados
./scripts/dr-test.sh
./scripts/dr-test.sh --include-bonsai
./scripts/validate-system-health.sh --full
