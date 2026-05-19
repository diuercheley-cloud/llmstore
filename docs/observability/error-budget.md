# Error Budget Guide

O Error Budget representa a quantidade de erros que podemos tolerar em um período (janela de 30 dias) sem violar o SLO.

## Cálculos
`Budget = (1 - SLO) * Total Requests`

Se o budget acabar, novas mudanças (que não sejam correções de estabilidade) devem ser congeladas.
