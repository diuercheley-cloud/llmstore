import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.config import Settings
from fastapi import Request

PUBLIC_STATIC_DIR = Path(__file__).resolve().parents[1] / "static" / "www"


@dataclass(frozen=True)
class PublicPageSEO:
    slug: str
    path: str
    file_name: str
    title: str
    description: str
    keywords: tuple[str, ...]
    og_type: str = "website"
    change_frequency: str = "monthly"
    priority: float = 0.7
    should_index: bool = True
    schema_types: tuple[str, ...] = ("Organization", "SoftwareApplication")


PUBLIC_PAGES: dict[str, PublicPageSEO] = {
    "landing": PublicPageSEO(
        slug="landing",
        path="/",
        file_name="index.html",
        title="LLM Inference Stack | Infraestrutura privada de IA com API compatível com OpenAI",
        description="Stack privada para inferência de LLM com API compatível com OpenAI, RAG nativo, portal do cliente e operação em infraestrutura própria.",
        keywords=("llm inference stack", "openai compatible api", "private ai", "rag", "infraestrutura de ia"),
        change_frequency="weekly",
        priority=1.0,
        schema_types=("Organization", "Product", "SoftwareApplication"),
    ),
    "pricing": PublicPageSEO(
        slug="pricing",
        path="/pricing",
        file_name="pricing.html",
        title="Pricing | LLM Inference Stack",
        description="Planos simples para infraestrutura de inferência de IA com endpoints compatíveis com OpenAI, quotas previsíveis e suporte empresarial.",
        keywords=("llm pricing", "openai compatible api pricing", "private ai pricing", "rag pricing"),
        priority=0.9,
        schema_types=("Organization", "Product", "SoftwareApplication"),
    ),
    "docs": PublicPageSEO(
        slug="docs",
        path="/docs",
        file_name="docs.html",
        title="Documentação da API | LLM Inference Stack",
        description="Referência técnica da API compatível com OpenAI, com exemplos de integração, autenticação e chamadas de chat completions.",
        keywords=("api docs", "openai compatible docs", "llm api", "chat completions api"),
        change_frequency="weekly",
        priority=0.85,
        schema_types=("Organization", "SoftwareApplication"),
    ),
    "examples": PublicPageSEO(
        slug="examples",
        path="/examples",
        file_name="examples.html",
        title="Exemplos de Integração | LLM Inference Stack",
        description="Exemplos práticos em curl, Python e Node.js para usar a API compatível com OpenAI da stack local.",
        keywords=("examples llm api", "openai compatible examples", "curl python node llm"),
        priority=0.7,
        schema_types=("Organization", "SoftwareApplication"),
    ),
    "capabilities": PublicPageSEO(
        slug="capabilities",
        path="/capabilities",
        file_name="capabilities.html",
        title="Capabilities | LLM Inference Stack",
        description="Veja recursos suportados, estágios de disponibilidade e limitações do appliance local de IA e da stack de inferência.",
        keywords=("llm capabilities", "local ai appliance", "inference stack features", "openai compatible"),
        priority=0.8,
        schema_types=("Organization", "Product", "SoftwareApplication"),
    ),
    "getting_started": PublicPageSEO(
        slug="getting-started",
        path="/getting-started",
        file_name="getting-started.html",
        title="Getting Started | LLM Inference Stack",
        description="Guia rápido para criar sua conta, acessar o portal do cliente e executar o primeiro prompt na stack de inferência.",
        keywords=("getting started llm", "onboarding api", "llm setup", "client portal"),
        priority=0.65,
        schema_types=("Organization", "SoftwareApplication"),
    ),
    "signup": PublicPageSEO(
        slug="signup",
        path="/signup",
        file_name="signup.html",
        title="Criar Conta | LLM Inference Stack",
        description="Crie sua conta, selecione um plano e receba uma API key para começar a usar a infraestrutura de LLM em minutos.",
        keywords=("signup llm", "api key signup", "llm onboarding", "private ai account"),
        change_frequency="weekly",
        priority=0.75,
        schema_types=("Organization", "Product", "SoftwareApplication"),
    ),
}


@lru_cache(maxsize=16)
def _load_public_page(file_name: str) -> str:
    return (PUBLIC_STATIC_DIR / file_name).read_text(encoding="utf-8")


def _base_url(request: Request, settings: Settings) -> str:
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def absolute_url(base_url: str, path: str) -> str:
    if path == "/":
        return base_url
    return f"{base_url}{path}"


def build_json_ld(page: PublicPageSEO, *, request: Request, settings: Settings) -> list[dict[str, Any]]:
    base_url = _base_url(request, settings)
    page_url = absolute_url(base_url, page.path)
    image_url = absolute_url(base_url, "/static/www/og-default.png")
    organization = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": settings.public_brand_name,
        "url": base_url,
        "logo": image_url,
        "contactPoint": [
            {
                "@type": "ContactPoint",
                "contactType": "sales",
                "email": settings.public_support_email,
                "availableLanguage": ["en", "pt-BR"],
            }
        ],
    }
    product = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": settings.public_brand_name,
        "description": page.description,
        "brand": {
            "@type": "Brand",
            "name": settings.public_brand_name,
        },
        "image": image_url,
        "url": page_url,
        "category": "AI Inference Platform",
    }
    software = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": settings.public_brand_name,
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Linux, Docker, Kubernetes",
        "description": page.description,
        "url": page_url,
        "image": image_url,
        "offers": {
            "@type": "Offer",
            "url": absolute_url(base_url, "/pricing"),
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
        },
        "publisher": {
            "@type": "Organization",
            "name": settings.public_brand_name,
        },
    }
    schema_by_type = {
        "Organization": organization,
        "Product": product,
        "SoftwareApplication": software,
    }
    return [schema_by_type[schema_type] for schema_type in page.schema_types]


def build_analytics_snippet(settings: Settings) -> str:
    provider = settings.public_analytics_provider.lower().strip()
    if provider != "plausible":
        return ""
    domain = settings.public_plausible_domain.strip()
    if not domain:
        parsed = urlparse(settings.public_base_url)
        domain = parsed.netloc
    if not domain:
        return ""
    script_src = settings.public_plausible_src.strip() or "https://plausible.io/js/script.js"
    return (
        f'<script defer data-domain="{html.escape(domain)}" '
        f'src="{html.escape(script_src)}"></script>'
    )


def build_meta_head(page: PublicPageSEO, *, request: Request, settings: Settings) -> str:
    base_url = _base_url(request, settings)
    page_url = absolute_url(base_url, page.path)
    image_url = absolute_url(base_url, "/static/www/og-default.png")
    robots_content = "index,follow,max-image-preview:large"
    keywords = ", ".join(page.keywords)
    twitter_site = ""
    if settings.public_support_email:
        twitter_site = f'<meta name="twitter:label1" content="Support" />\n    <meta name="twitter:data1" content="{html.escape(settings.public_support_email)}" />'
    json_ld = "\n".join(
        f'<script type="application/ld+json">{json.dumps(item, ensure_ascii=False)}</script>'
        for item in build_json_ld(page, request=request, settings=settings)
    )
    analytics = build_analytics_snippet(settings)
    return f"""
    <meta name="description" content="{html.escape(page.description)}" />
    <meta name="keywords" content="{html.escape(keywords)}" />
    <meta name="robots" content="{robots_content}" />
    <link rel="canonical" href="{html.escape(page_url)}" />
    <meta property="og:locale" content="pt_BR" />
    <meta property="og:type" content="{html.escape(page.og_type)}" />
    <meta property="og:title" content="{html.escape(page.title)}" />
    <meta property="og:description" content="{html.escape(page.description)}" />
    <meta property="og:image" content="{html.escape(image_url)}" />
    <meta property="og:url" content="{html.escape(page_url)}" />
    <meta property="og:site_name" content="{html.escape(settings.public_brand_name)}" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{html.escape(page.title)}" />
    <meta name="twitter:description" content="{html.escape(page.description)}" />
    <meta name="twitter:image" content="{html.escape(image_url)}" />
    {twitter_site}
    {json_ld}
    {analytics}
""".rstrip()


def render_public_page(page: PublicPageSEO, *, request: Request, settings: Settings) -> str:
    source = _load_public_page(page.file_name)
    rendered = re.sub(
        r"<title>.*?</title>",
        f"<title>{html.escape(page.title)}</title>",
        source,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return rendered.replace("</head>", f"{build_meta_head(page, request=request, settings=settings)}\n  </head>", 1)


def generate_sitemap(*, request: Request, settings: Settings) -> str:
    base_url = _base_url(request, settings)
    url_entries = []
    for page in PUBLIC_PAGES.values():
        file_path = PUBLIC_STATIC_DIR / page.file_name
        url_entries.append(
            {
                "loc": absolute_url(base_url, page.path),
                "changefreq": page.change_frequency,
                "priority": f"{page.priority:.1f}",
                "lastmod": datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d"),
            }
        )
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for entry in url_entries:
        lines.extend(
            [
                "  <url>",
                f"    <loc>{html.escape(entry['loc'])}</loc>",
                f"    <lastmod>{entry['lastmod']}</lastmod>",
                f"    <changefreq>{entry['changefreq']}</changefreq>",
                f"    <priority>{entry['priority']}</priority>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")
    return "\n".join(lines)


def generate_robots_txt(*, request: Request, settings: Settings) -> str:
    base_url = _base_url(request, settings)
    sitemap_url = absolute_url(base_url, "/sitemap.xml")
    return "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin-dashboard",
            "Disallow: /admin-v2",
            "Disallow: /admin-lab",
            "Disallow: /admin-tests",
            "Disallow: /client-portal",
            "Disallow: /portal/",
            "Disallow: /v1/",
            "Disallow: /admin/",
            "Disallow: /static/admin/",
            "Disallow: /static/admin-v2/",
            "Disallow: /static/admin-lab/",
            f"Sitemap: {sitemap_url}",
        ]
    )
