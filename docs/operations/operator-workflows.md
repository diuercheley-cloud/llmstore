---
owner: platform-ops
status: consolidated
---

# Workflows de Operação

Guia prático para operadores do LLM Inference Stack.

## 1. Tratamento de Incidentes de Latência

1. Acesse **Operations > Incident Timeline** para verificar se há eventos globais conhecidos.
2. Verifique **Operations > Queue / QoS** para identificar se há sobrecarga em algum tier específico.
3. Analise **Operations > Runtime Nodes** para encontrar nós com alto consumo de recursos ou falhas de heartbeat.
4. Se um nó estiver instável, utilize a ação **Drain** e investigue os logs do container.

## 2. Manutenção Programada de Nó

1. No painel **Runtime Nodes**, localize o nó alvo.
2. Clique no ícone de **Drain**.
3. Aguarde até que o status mude para `Draining` (completando tarefas atuais).
4. Quando o nó não tiver mais requisições ativas, realize a manutenção física/virtual.
5. Após reiniciar o serviço no nó, ele voltará automaticamente ao pool como `Ready`.

## 3. Rollback de Modelo Após Falha de Versão

1. Se novos deploys de modelos causarem erros (5xx), vá para **Operations > Model Runtime**.
2. Localize o modelo afetado.
3. Clique em **Rollback** para retornar à última versão estável conhecida.
4. Verifique a estabilização em **Operations > Overview**.

## 4. Auditoria de Segurança Semanal

1. Acesse **Operations > Security Posture**.
2. Revise os "Últimos Eventos de Segurança".
3. Clique em **Baixar Relatório** para obter o sumário em PDF para conformidade (SOC2/ISO27001).
