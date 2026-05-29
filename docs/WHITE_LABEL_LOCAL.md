---
owner: platform-ops
status: consolidated
---

# White-Label Local — Branding Personalizado

Este módulo permite personalizar a identidade visual e textual do **LLM Inference Stack** em modo **Local Appliance** sem alterar código-fonte.

## Configuração

Crie o arquivo `config/branding.local.json` copiando o exemplo:

```bash
cp config/branding.example.json config/branding.local.json
```

Edite os campos conforme necessidade:

```json
{
  "product_name": "Meu Produto AI",
  "company_name": "Minha Empresa",
  "tagline": "IA Privada para sua Empresa",
  "support_email": "suporte@minhaempresa.com",
  "primary_color": "#2563eb",
  "secondary_color": "#0f766e",
  "footer_text": "© 2026 Minha Empresa. Todos os direitos reservados.",
  "show_powered_by": true,
  "capabilities_title": "Recursos & Funcionalidades"
}
```

> **AVISO:** `config/branding.local.json` está no `.gitignore` e **não deve ser versionado**. Use apenas o `.example.json` como referência no repositório.

## Campos

| Campo | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `product_name` | string | `LLM Inference Stack` | Nome do produto exibido no navbar e título |
| `company_name` | string | `LLM Inference Stack` | Nome da empresa/fornecedor |
| `tagline` | string | `LLM Local para Empresas` | Subtítulo/Slogan na landing page |
| `support_email` | string | `suporte@example.com` | E-mail de suporte |
| `primary_color` | hex | `#c84c2f` | Cor principal (navbar, botões, acentos) |
| `secondary_color` | hex | `#0f766e` | Cor secundária |
| `footer_text` | string | `© 2026 LLM Inference Stack...` | Texto do rodapé |
| `show_powered_by` | bool | `true` | Exibir/ocultar selo "Powered by" |
| `capabilities_title` | string | `Capabilities & Features` | Título da página de capacidades |

## Endpoint Público

```http
GET /public/branding
```

Retorna o branding seguro (sem secrets, sem dados sensíveis):

```json
{
  "product_name": "Meu Produto AI",
  "company_name": "Minha Empresa",
  ...
  "show_powered_by": true
}
```

## Páginas Afetadas

- Landing page (`/`)
- Capabilities (`/capabilities`)
- Pricing (`/pricing`)
- Signup (`/signup`)
- Docs (`/docs`)
- Getting Started (`/getting-started`)
- Admin Dashboard (`/admin-dashboard`)
- Admin Lab (`/admin-lab`)
- Admin Tests (`/admin-tests`)
- Client Portal (`/client-portal`)
- System Monitoring (`/monitoring`)

## Propostas Comerciais

Os templates de proposta em `proposals/` contêm placeholders para nome do produto. Para white-label completo em propostas, substitua manualmente as referências a "LLM Inference Stack" ou utilize o script de geração de propostas.

## Segurança

- O arquivo `branding.local.json` **não é servido estaticamente**.
- O endpoint `/public/branding` sanitiza strings (remove HTML, limita tamanho).
- Cores inválidas são ignoradas (fallback para default).
- O serviço nunca falha se o arquivo estiver ausente ou corrompido.
- Nenhum secret é exposto pelo endpoint de branding.

## Validação

```bash
make validate-white-label
```
