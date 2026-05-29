---
owner: platform-ops
status: consolidated
---

# Transparency Gossip & Consistency Checks

Mecanismo de detecção de divergência e auditoria descentralizada para garantir a integridade global das provas de execução.

## Objetivo
Detectar "Split-View" (visões divergentes do estado do sistema) entre clusters, testemunhas e auditores externos, garantindo que todos os participantes observem a mesma Merkle Root para um determinado período.

## Componentes

### 1. Consistency Checkpoints
Resumos periódicos (ex: a cada 60 minutos) que agregam as raízes de Merkle das timelines seladas no período.
- **Root Hash**: Hash SHA-256 de todas as Merkle Roots do período.
- **Witness Summary**: Evidência do quorum alcançado durante o fechamento das timelines.

### 2. Transparency Gossip
Protocolo de troca de checkpoints entre peers conhecidos (Clusters, Witnesses, Auditores).
- **Push/Pull**: Troca ativa ou reativa de metadados de integridade.
- **Sanitized Payloads**: Apenas hashes e metadados de auditoria são trocados; nenhum dado de prompt ou resposta sai do cluster.

### 3. Split-View Detection
Alerta crítico gerado quando dois checkpoints para o mesmo período possuem hashes diferentes.
- **Severidade Crítica**: Indica possível manipulação de dados ou comprometimento de infraestrutura.
- **Resolução**: Exige intervenção administrativa para reconciliação de evidências.

## Configuração
```env
COMMERCIAL_TRANSPARENCY_GOSSIP_ENABLED=true
COMMERCIAL_TRANSPARENCY_GOSSIP_MODE=dry_run
COMMERCIAL_TRANSPARENCY_CHECKPOINT_INTERVAL_MINUTES=60
COMMERCIAL_TRANSPARENCY_SPLIT_VIEW_ALERTS=true
```

## Verificação Offline
O `Public Verifier CLI` suporta a comparação de um `Execution Proof` individual contra um `Consistency Checkpoint` global:
```bash
python verifier_cli.py verify proof.json --checkpoint checkpoint.json
```
Se a raiz da timeline no `proof.json` não estiver incluída ou não bater com o `checkpoint.json`, um aviso de **SPLIT_VIEW_DETECTION** será exibido.
