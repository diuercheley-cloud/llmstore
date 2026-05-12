# Contratos / Templates Comerciais — Local AI Appliance

Este diretório contém **templates de contratos e SOW (Statement of Work)** para a implantação do **LLM Inference Stack** em modo **Local Appliance**.

## Aviso Importante

> **ESTES DOCUMENTOS SÃO TEMPLATES GENÉRICOS. NÃO CONSTITUEM ACONSELHAMENTO JURÍDICO E NÃO DISPENSAM REVISÃO POR ASSESSORIA JURÍDICA QUALIFICADA.**
>
> - Não inclua dados reais de clientes nestes templates.
> - Não prometa garantias absolutas de funcionamento, segurança ou compliance.
> - Não prometa compliance automático com LGPD, HIPAA ou qualquer outra regulação.
> - Não prometa processamento de pagamentos reais via PSP/PIX (o sistema opera em modo simulado/local).
> - Não versionar contratos preenchidos com dados reais.

## Templates Disponíveis

| Arquivo | Descrição |
|---------|-----------|
| `SOW_TEMPLATE.md` | Statement of Work — escopo, entregáveis, cronograma, critérios de aceite |
| `SERVICE_AGREEMENT_TEMPLATE.md` | Contrato de prestação de serviços — responsabilidades, disponibilidade, propriedade dos dados |
| `SUPPORT_TERMS_TEMPLATE.md` | Termos de suporte — níveis, SLA, canais, exclusões |
| `ACCEPTANCE_CRITERIA_TEMPLATE.md` | Critérios formais de aceite para implantação |
| `README.md` | Este arquivo |

## Uso

1. Copie o template relevante para `artifacts/contracts/<cliente>/`.
2. Preencha os placeholders (dados do cliente, valores, prazos).
3. **Submeta ao jurídico para revisão obrigatória antes de qualquer assinatura.**
4. Não versione contratos preenchidos no repositório.

## Scripts Relacionados

```bash
# Gerar SOW personalizado para um cliente
./scripts/generate-sow-local.sh --company-name "Cliente" --project-name "Projeto" --plan "Pro"

# Validar integridade dos templates
./scripts/validate-contract-templates-local.sh
```

## Geração

SOWs personalizados são gerados em `artifacts/contracts/` (diretório ignorado pelo Git).

---

*Template v1.0 — LLM Inference Stack — Sales Ops*
