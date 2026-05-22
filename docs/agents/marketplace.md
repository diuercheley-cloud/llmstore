# Agent Marketplace

O Agent Marketplace permite a descoberta, instalação e gestão de templates de agentes pré-configurados (Agent Bundles).

## Agent Bundles

Um Agent Bundle é um pacote distribuível que contém tudo o que é necessário para executar um agente especializado:

- **manifest.json**: Metadados do pacote (nome, versão, autor, assinatura).
- **Agent Definition**: Instruções, modelo e ferramentas permitidas.
- **Tool Requirements**: Lista de ferramentas necessárias para o funcionamento do agente.
- **Memory Policy**: Regras de retenção de dados recomendadas.
- **Eval Suite**: Conjunto de testes para validar a performance do agente após a instalação.

## Instalação

A instalação é realizada através do upload do bundle. O sistema valida:

1. **Assinatura**: Se `AGENT_BUNDLE_SIGNATURE_REQUIRED` estiver ativo, apenas bundles assinados por autoridades confiáveis podem ser instalados.
2. **Integridade**: Verificação de checksums dos componentes do bundle.
3. **Compatibilidade**: Versão mínima da plataforma suportada.
4. **Governança**: O agente instalado inicia em modo `installed` e deve ser habilitado e promovido para produção seguindo as regras de governança padrão (baseline de evals, etc).

## Exemplos Disponíveis

- `support-triage-agent`: Classificação automática de tickets.
- `compliance-evidence-agent`: Coleta de evidências para auditorias SOC2/ISO.
- `ops-readiness-agent`: Verificação de saúde de infraestrutura.
- `billing-review-agent`: Auditoria de faturas e consumo.
- `rag-research-agent`: Pesquisa avançada em base de conhecimento RAG.
