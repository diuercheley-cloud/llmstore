# Propostas Comerciais e Técnicas — llm-inference-stack

Este diretório contém templates de propostas para apresentação do **llm-inference-stack** (appliance local de LLM-as-a-Service) a clientes. Os arquivos Markdown são a **fonte versionável** — PDFs são gerados localmente sob demanda e não devem ser versionados.

## Estrutura

| Arquivo | Descrição |
|---------|-----------|
| `TECHNICAL_PROPOSAL_TEMPLATE.md` | Proposta técnica detalhada: arquitetura, componentes, requisitos, segurança, implantação |
| `COMMERCIAL_PROPOSAL_TEMPLATE.md` | Proposta comercial: problema, solução, planos, custos (placeholders), cronograma |
| `LOCAL_AI_APPLIANCE_ONE_PAGER.md` | One-pager resumido para apresentação executiva rápida |
| `README.md` | Este arquivo |

## Geração de PDF

```bash
# Usar script de geração automática
./scripts/legacy/generate-proposal-pdf.sh --input proposals/TECHNICAL_PROPOSAL_TEMPLATE.md --output proposals/generated/proposta-tecnica.pdf

# Ver ajuda
./scripts/legacy/generate-proposal-pdf.sh --help
```

Ferramentas suportadas (detectadas automaticamente): `pandoc`, `wkhtmltopdf`, `google-chrome` (headless).

## Validação

```bash
./scripts/legacy/validate-proposals-local.sh
```

## Regras

- **Não versionar PDFs gerados.** A pasta `proposals/generated/` está em `.gitignore`.
- **Não incluir dados reais de clientes.** Use `[Nome do Cliente]`, `[Data]` como placeholders.
- **Não incluir preços definitivos sem política clara.** Use `R$ [ Valor ]` ou "Sob consulta".
- **Não prometer PSP/PIX real.** Especificar que billing é manual/local.
- **Não prometer SLA não contratado.** SLA depende do plano contratado.

## Gerador de Propostas Personalizadas

Para automatizar a criação de propostas preenchidas para clientes específicos, utilize o script de geração:

```bash
./scripts/dev/generate-client-proposal.sh --company-name "Nome da Empresa" --segment "Saúde" --plan "Pro"
```

### Funcionalidades:
- Integração com CRM (via `--lead-id`).
- Geração automática de seções de diagnóstico, escopo, valores e cronograma.
- Criação de metadata JSON para integração com outros sistemas.
- Suporte opcional a PDF (via `generate-proposal-pdf.sh`).

As propostas geradas em `artifacts/proposals/` são ignoradas pelo Git por padrão.

## Contratos e SOW

Templates de contrato e SOW para implantação local estão disponíveis em `contracts/`. Consulte `contracts/README.md` para detalhes.

```bash
# Gerar SOW personalizado
./scripts/dev/generate-sow-local.sh --company-name "Cliente" --project-name "Local AI Appliance" --plan Pro

# Validar templates
./scripts/validators/validate-contract-templates-local.sh
```

**AVISO:** Todos os templates exigem revisão jurídica obrigatória. Não versionar contratos preenchidos no repositório.
