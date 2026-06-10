# Política de Depreciação de Feature Flags (Sunset Policy)

Devido ao crescimento da plataforma, o número de Feature Flags ultrapassou limites sustentáveis, gerando alta complexidade ciclomática e dificuldade de manutenção (Tech Debt).

Para mitigar isso, introduzimos o processo de **Sunset de Flags**:

## Regras de Consolidação

1. **Tempo de Vida (Lifespan)**:
   - Qualquer flag introduzida com status `beta` ou `internal` que atinja maturidade deve ser promovida para `ga`.
   - Flags em `ga` (General Availability) que se tornam o comportamento padrão da plataforma e rodam sem incidentes por **2 versões menores (minor releases)** (ex: introduzido em `v1.6`, estável em `v1.8`) devem ser obrigatoriamente consolidadas.

2. **Processo de Depreciação**:
   - O comportamento condicionado pela flag torna-se permanente no código base.
   - O código condicional (If/Else) é limpo.
   - A flag é mantida temporariamente em `config/feature-flags.yaml` com o atributo `status: deprecated` para não quebrar instâncias locais que ainda a passem no ambiente.
   - Após 1 versão adicional, a flag é removida totalmente.

## Execução

Durante o ciclo de QA pré-release, os Tech Leads devem revisar o relatório de *Feature Flag Drift* gerado no CI e abrir PRs de limpeza para remover flags elegíveis.

## Automação

No futuro, um script de auditoria do CI falhará se detectar flags elegíveis para consolidação que não tenham sido atualizadas no registro YAML.
