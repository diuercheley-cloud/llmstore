# Data Boundaries & Sovereignty

Garantir a soberania dos dados em operações multi-cluster é fundamental.

## Regras de Ouro
1. **Prompts**: Ficam no cluster onde a requisição foi originada.
2. **Documentos**: Persistem apenas no cluster de armazenamento local.
3. **Logs**: Logs de auditoria são agregados, mas anonimizados antes do transporte cross-cluster.
