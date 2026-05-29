---
owner: platform-ops
status: consolidated
---

# SEO do Frontend Público

Esta documentação resume as meta tags e os dados estruturados aplicados às páginas públicas servidas por `control_plane/app/api/public.py`.

## Implementação

- Renderização SEO server-side por rota usando [control_plane/app/services/public_seo.py](/home/kleber/llm-inference-stack/control_plane/app/services/public_seo.py)
- Open Graph: `og:title`, `og:description`, `og:image`, `og:url`, `og:site_name`, `og:locale`
- Twitter Cards: `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`
- Canonical: `link rel="canonical"`
- Busca: `meta name="robots"` com `index,follow,max-image-preview:large`
- JSON-LD: `Organization`, `Product`, `SoftwareApplication`
- Sitemap: `/sitemap.xml`
- Robots: `/robots.txt`
- Analytics privacidade-first: Plausible opcional via `PUBLIC_ANALYTICS_PROVIDER=plausible`

## Meta Tags por Página

| Página | Path | Title | Meta Description | Schema.org |
| --- | --- | --- | --- | --- |
| Landing | `/` | `LLM Inference Stack \| Infraestrutura privada de IA com API compatível com OpenAI` | `Stack privada para inferência de LLM com API compatível com OpenAI, RAG nativo, portal do cliente e operação em infraestrutura própria.` | `Organization`, `Product`, `SoftwareApplication` |
| Pricing | `/pricing` | `Pricing \| LLM Inference Stack` | `Planos simples para infraestrutura de inferência de IA com endpoints compatíveis com OpenAI, quotas previsíveis e suporte empresarial.` | `Organization`, `Product`, `SoftwareApplication` |
| Docs | `/docs` | `Documentação da API \| LLM Inference Stack` | `Referência técnica da API compatível com OpenAI, com exemplos de integração, autenticação e chamadas de chat completions.` | `Organization`, `SoftwareApplication` |
| Capabilities | `/capabilities` | `Capabilities \| LLM Inference Stack` | `Veja recursos suportados, estágios de disponibilidade e limitações do appliance local de IA e da stack de inferência.` | `Organization`, `Product`, `SoftwareApplication` |
| Getting Started | `/getting-started` | `Getting Started \| LLM Inference Stack` | `Guia rápido para criar sua conta, acessar o portal do cliente e executar o primeiro prompt na stack de inferência.` | `Organization`, `SoftwareApplication` |
| Signup | `/signup` | `Criar Conta \| LLM Inference Stack` | `Crie sua conta, selecione um plano e receba uma API key para começar a usar a infraestrutura de LLM em minutos.` | `Organization`, `Product`, `SoftwareApplication` |

## Variáveis de Ambiente

- `PUBLIC_BASE_URL`: domínio canônico público, usado em canonical, OG URL, sitemap e robots.
- `PUBLIC_BRAND_NAME`: nome da marca exibido em `og:site_name` e JSON-LD.
- `PUBLIC_SUPPORT_EMAIL`: contato publicado em JSON-LD e Twitter metadata complementar.
- `PUBLIC_ANALYTICS_PROVIDER`: `none` ou `plausible`.
- `PUBLIC_PLAUSIBLE_DOMAIN`: domínio do site rastreado pelo Plausible.
- `PUBLIC_PLAUSIBLE_SRC`: URL do script do Plausible. Default: `https://plausible.io/js/script.js`.

## Observações

- A imagem social padrão é [control_plane/app/static/www/og-default.png](/home/kleber/llm-inference-stack/control_plane/app/static/www/og-default.png).
- `robots.txt` bloqueia superfícies administrativas e portal autenticado para evitar indexação indevida.
- `sitemap.xml` é gerado automaticamente a partir da definição central de rotas públicas estáticas.
