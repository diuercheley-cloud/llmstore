#!/usr/bin/env python3
"""Generate detailed .docx report of the LLM Inference Stack system."""

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
import subprocess, os

doc = Document()

style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(10)

sections = doc.sections
for section in sections:
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)

def add_heading(text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x1a, 0x1a, 0x2e)
    return h

def add_bold_text(text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    p.space_after = Pt(2)
    return p

def add_item(label, value=""):
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(label + ": ")
    run.bold = True
    p.add_run(str(value))
    p.space_after = Pt(1)
    return p

def add_table(headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    hdr = table.rows[0]
    for i, h in enumerate(headers):
        hdr.cells[i].text = h
    for row_data in rows:
        row = table.add_row()
        for i, val in enumerate(row_data):
            row.cells[i].text = str(val)
    return table

def add_paragraph(text):
    p = doc.add_paragraph(text)
    p.space_after = Pt(3)
    return p

def get_git_log():
    try:
        r = subprocess.run(['git', 'log', '--oneline', '-30'],
                           capture_output=True, text=True, cwd=os.getcwd())
        return r.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def get_dir_size(path):
    try:
        r = subprocess.run(['du', '-sh', '--exclude=.git', '--exclude=.venv', '--exclude=__pycache__', path],
                           capture_output=True, text=True, cwd=path)
        return r.stdout.split()[0] if r.stdout.strip() else "?"
    except:
        return "?"

def count_files(path):
    total = 0
    for root, dirs, files in os.walk(path):
        if '.git' in root or '.venv' in root or '__pycache__' in root or '.mypy_cache' in root or '.pytest_cache' in root or '.ruff_cache' in root:
            continue
        total += len(files)
    return total

# ============================================================
#  TITLE PAGE
# ============================================================
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("LLM Inference Stack\nRelatório Detalhado do Sistema")
run.font.size = Pt(24)
run.bold = True
run.font.color.rgb = RGBColor(0x1a, 0x1a, 0x2e)

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run("v2.x-agentic-production-trust-hardening")
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(0x55, 0x55, 0x77)

meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta.add_run(f"Gerado em: 05/06/2026\n"
             f"Diretório: {os.getcwd()}\n"
             f"Tamanho total: {get_dir_size(os.getcwd())}").font.size = Pt(10)

doc.add_page_break()

# ============================================================
#  1. VISÃO GERAL
# ============================================================
add_heading("1. Visão Geral do Sistema", 1)

add_paragraph(
    "O LLM Inference Stack é uma plataforma de IA soberana, offline-first e determinística "
    "com runtime de agente governado. Trata-se de uma infraestrutura de IA on-premise full-stack "
    "compatível com a API da OpenAI, projetada para execução exclusivamente em hardware local "
    "(Linux ou WSL2) sem nenhuma dependência de nuvem."
)

add_item("Versão Atual", "v2.x-agentic-production-trust-hardening")
add_item("Propósito", "Plataforma de inferência LLM + runtime de agentes com governança, billing, multi-tenancy")
add_item("Tipo", "On-premise / Sovereign Cloud / Appliance")
add_item("Linguagens", "Python 3.12+, TypeScript 6, Go 1.22")
add_item("Total de Arquivos", str(count_files(os.getcwd())))
add_item("Tamanho (excluindo .git/.venv)", get_dir_size(os.getcwd()))
add_item("Commits Recentes", get_git_log().split('\n')[0] if get_git_log() else "")

doc.add_paragraph()

# ============================================================
#  2. ARQUITETURA
# ============================================================
add_heading("2. Arquitetura", 1)

add_heading("2.1 Stack Tecnológico", 2)
add_table(
    ["Tecnologia", "Uso"],
    [
        ["Python 3.12+", "Backend principal"],
        ["FastAPI", "Web framework (Control Plane)"],
        ["SQLAlchemy 2.0", "ORM assíncrono"],
        ["Alembic", "Migrações de banco de dados"],
        ["PostgreSQL 16", "Banco de dados primário"],
        ["Redis 7", "Cache, fila, pub/sub"],
        ["Pydantic v2", "Validação de dados e settings"],
        ["React 19 + TypeScript", "Frontend (Admin + Client Portal)"],
        ["Vite 8", "Build tool frontend"],
        ["Tailwind CSS v4", "Estilização frontend"],
        ["Docker / Docker Compose", "Orquestração de containers"],
        ["Kubernetes", "Orquestração enterprise"],
        ["Helm", "Package manager K8s"],
        ["Kopf", "Framework de operadores K8s"],
        ["llama.cpp", "Inferência local (modelos GGUF)"],
        ["Prometheus + Grafana", "Métricas e dashboards"],
        ["OpenTelemetry", "Tracing distribuído"],
        ["Loki + Tempo", "Agregação de logs e traces"],
    ]
)

add_heading("2.2 Bounded Contexts (12 Domínios)", 2)
add_table(
    ["Contexto", "Descrição"],
    [
        ["core_runtime", "Abstrações determinísticas de runtime"],
        ["governance", "Engine de políticas, aprovações, compliance"],
        ["federation", "Contratos de federação offline-first"],
        ["plugin_runtime", "Carregamento de plugins, sandbox ABI"],
        ["supply_chain", "Proveniência, linhagem de artefatos, reprodutibilidade"],
        ["operations", "Workflows determinísticos, eventos, recuperação"],
        ["security", "Limites de confiança, criptografia, isolamento"],
        ["financial", "Faturamento, governança financeira"],
        ["sovereign", "Airgap, localidade, soberania do tenant"],
        ["observability", "Métricas locais, traces, visibilidade sanitizada"],
        ["data_governance", "Zoneamento de dados, linhagem, retenção"],
        ["disaster_recovery", "Manifestos de backup, verificação de replay"],
    ]
)

# ============================================================
#  3. ESTRUTURA DE DIRETÓRIOS
# ============================================================
add_heading("3. Estrutura de Diretórios", 1)

add_paragraph("O repositório contém mais de 2.500 arquivos organizados nos seguintes diretórios principais:")

add_table(
    ["Diretório", "Conteúdo", "Arquivos"],
    [
        ["control_plane/", "Backend FastAPI principal", str(count_files("control_plane"))],
        ["frontend/", "SPAs React (admin + client portal)", str(count_files("frontend"))],
        ["scripts/", "Scripts operacionais (~518)", str(count_files("scripts"))],
        ["tests/", "Testes pytest (~647)", str(count_files("tests"))],
        ["docker/", "Contextos de build Docker", str(count_files("docker"))],
        ["config/", "Configurações YAML/JSON (25+)", str(count_files("config"))],
        ["docs/", "Documentação (~204 arquivos)", str(count_files("docs"))],
        ["deploy/", "Helm charts + manifests K8s", str(count_files("deploy"))],
        ["sdk/", "SDKs Python/Node/Go", str(count_files("sdk"))],
        ["monitoring/", "Prometheus, Grafana, OTEL, Loki, Tempo", str(count_files("monitoring"))],
        ["operator/", "Operador Kubernetes (Kopf)", str(count_files("operator"))],
        ["commercial/", "Templates de vendas/SOW", str(count_files("commercial"))],
        ["models/", "Modelos GGUF (Gemma 4, test)", str(count_files("models"))],
        ["data/", "PKI, plugins, RAG uploads", str(count_files("data"))],
        ["contracts/", "Contratos jurídicos", str(count_files("contracts"))],
        ["proposals/", "Propostas comerciais", str(count_files("proposals"))],
        ["releases/", "Bundles de release (21 versões)", str(count_files("releases"))],
        ["reports/", "Relatórios gerados", str(count_files("reports"))],
        ["artifacts/", "Artefatos de build/test", str(count_files("artifacts"))],
        ["chaos/", "Experimentação de caos", str(count_files("chaos"))],
        ["examples/", "Exemplos de integração", str(count_files("examples"))],
        ["demo-pack/", "Materiais de demonstração", str(count_files("demo-pack"))],
        ["data_plane_mock/", "Mock do data plane", str(count_files("data_plane_mock"))],
        ["bin/", "Binários llama.cpp pré-compilados", str(count_files("bin"))],
    ]
)

# ============================================================
#  4. CONTROL PLANE (BACKEND)
# ============================================================
add_heading("4. Control Plane - Backend (FastAPI)", 1)

add_paragraph(
    "O Control Plane é o backend principal, implementado em Python com FastAPI assíncrono. "
    "Contém ~188 routers registrados, ~150 modelos de banco de dados e ~96 módulos de serviço."
)

add_heading("4.1 Estrutura Interna", 2)
add_table(
    ["Caminho", "Descrição"],
    [
        ["control_plane/app/main.py", "Entry point, registro de ~188 routers"],
        ["control_plane/app/core/config.py", "Configuração (Pydantic Settings, 1840 linhas)"],
        ["control_plane/app/core/security.py", "Utilitários de segurança"],
        ["control_plane/app/core/metrics.py", "Métricas Prometheus"],
        ["control_plane/app/api/", "Routers da API (~188)"],
        ["control_plane/app/models/", "Modelos SQLAlchemy (~150)"],
        ["control_plane/app/schemas/", "Schemas Pydantic"],
        ["control_plane/app/services/", "Lógica de negócio (~96 módulos)"],
        ["control_plane/app/db/", "Sessão de BD, Redis"],
        ["control_plane/app/workers/", "Workers assíncronos"],
        ["control_plane/app/middleware.py", "Middleware CORS, rate limit, segurança"],
        ["control_plane/alembic/", "Migrações de BD (~140)"],
    ]
)

add_heading("4.2 Endpoints Principais da API", 2)
add_table(
    ["Grupo", "Rota", "Autenticação", "Descrição"],
    [
        ["Inferência", "/v1/chat/completions", "API Key", "Chat completion (OpenAI compatível)"],
        ["Inferência", "/v1/completions", "API Key", "Text completion"],
        ["Inferência", "/v1/embeddings", "API Key", "Embeddings"],
        ["Inferência", "/v1/models", "API Key", "Listar modelos"],
        ["Inferência", "/v1/audio/speech", "API Key", "Text-to-speech"],
        ["Inferência", "/v1/audio/transcriptions", "API Key", "Speech-to-text"],
        ["Inferência", "/v1/responses", "API Key", "Responses API simplificada"],
        ["Jobs", "/v1/jobs", "API Key", "CRUD de jobs assíncronos"],
        ["Agentes", "/v1/agents", "API Key", "OpenAI Assistants compatível"],
        ["Agents V1", "/v1/assistants", "X-Tenant-ID", "OpenAI Assistants v1"],
        ["RAG", "/v1/rag/query", "API Key", "Consulta RAG"],
        ["Chat Colab", "/v1/chat/channels", "Admin/Client", "Chat colaborativo WebSocket"],
        ["Admin", "/admin/clients", "Admin Token", "CRUD de clients/tenants"],
        ["Admin", "/admin/api-keys", "Admin Token", "Gerenciamento de chaves"],
        ["Admin", "/admin/billing/plans", "Admin Token", "Planos de faturamento"],
        ["Admin", "/admin/harness/runs", "Admin Token", "LLM Harness runs"],
        ["Admin", "/admin/providers", "Admin Token", "Provedores de inferência"],
        ["Admin", "/admin/routing", "Admin Token", "Roteamento entre backends"],
        ["Admin", "/admin/rag", "Admin Token", "Gerenciamento RAG"],
        ["Admin", "/admin/agents/*", "Admin Token", "Gestão completa de agentes"],
        ["Admin", "/admin/security/*", "Admin Token", "PKI, atestação, compliance"],
        ["Admin", "/admin/rbac", "Admin Token", "RBAC de administradores"],
        ["Portal", "/portal/*", "API Key", "Portal do cliente (uso, faturas, wallet)"],
        ["Auth", "/auth/login/{provider}", "Nenhum", "OAuth2 (Google, GitHub)"],
        ["System", "/health, /ready, /status", "Nenhum", "Health checks"],
        ["System", "/metrics", "Nenhum", "Métricas Prometheus"],
        ["Público", "/pricing, /signup, /docs", "Nenhum", "Páginas públicas"],
    ]
)

add_heading("4.3 Modelos de Banco de Dados", 2)
add_paragraph("O banco de dados contém aproximadamente 150 modelos SQLAlchemy organizados em contextos:")

add_bold_text("Runtime Principal:")
add_item("clients", "Tenants com planos, cotas, rate limits")
add_item("api_keys", "Chaves de API hasheadas com escopos e IP allowlists")
add_item("inference_backends", "Backends de inferência (URL, healthcheck, limites)")
add_item("model_registry", "Registro de modelos com templates de prompt")
add_item("model_backend_routes", "Roteamento ponderado entre modelos e backends")
add_item("generation_jobs", "Jobs de inferência assíncrona")
add_item("request_logs", "Log de auditoria de todas as requisições")
add_item("billing_plans", "Planos com cotas (tokens, requests, RAG, TTS, embeddings)")
add_item("pricing_rules", "Preços por plano")
add_item("billing_invoices", "Faturas mensais")
add_item("usage_records", "Uso agregado por período")
add_item("quota_counter", "Contadores de cota em tempo real")
add_item("response_cache", "Cache de resposta por match exato")

add_bold_text("Plataforma de Agentes (80+ modelos):")
add_item("Agent Registry", "Definições, versões, configurações")
add_item("Agent Sessions", "Sessões persistentes")
add_item("Agent Execution", "Execuções, steps, ferramentas")
add_item("Agent Memory", "Memória de trabalho, longo prazo, cognitiva")
add_item("Agent Tools", "Registro de ferramentas, síntese, MCP")
add_item("Agent Knowledge Graph", "RAG em grafo com pgvector/pgRouting")
add_item("Agent Workflows", "Orquestração de workflows stateful")
add_item("Agent IAM", "Service principals, tokens delegados, OAuth")
add_item("Agent Marketplace", "Marketplace de agentes")
add_item("Agent Wallet", "Carteiras digitais para agentes")

add_bold_text("Comercial (150+ modelos):")
add_item("commercial_routing_config", "Configuração de roteamento QoS")
add_item("commercial_federation", "Federação entre clusters")
add_item("commercial_cryptographic_receipts", "Recibos criptográficos")
add_item("commercial_governance", "Políticas de governança")
add_item("commercial_revenue_*", "Proteção de receita, forecasting")
add_item("commercial_trust_graph", "Grafo de confiança")

add_bold_text("Operações (70+ modelos):")
add_item("Cluster registry", "Nós, GPUs, heartbeats")
add_item("Chaos experiments", "Experimentação de caos")
add_item("Adapters", "Sandbox, registro, promoção")

# ============================================================
#  5. MIDDLEWARE E AUTENTICAÇÃO
# ============================================================
add_heading("5. Middleware e Autenticação", 1)

add_heading("5.1 Middleware Stack", 2)
add_table(
    ["Middleware", "Função"],
    [
        ["CORS", "Origens configuráveis via CORS_ALLOW_ORIGINS"],
        ["request_context_middleware", "Payload size check, proteção SaaS, extração de tenant, "
         "rate limiting global/por tenant, correlation ID, resolução de IP, logging JSON estruturado, "
         "cabeçalhos de segurança (HSTS, CSP, X-Frame-Options, etc.)"],
        ["deprecation_middleware", "Rastreamento de API surface, headers de deprecação e sunset"],
    ]
)

add_heading("5.2 Autenticação", 2)
add_table(
    ["Esquema", "Mecanismo"],
    [
        ["Admin Token", "X-Admin-Token header com roles: admin_read, admin_write, super_admin"],
        ["Client API Key", "Authorization: Bearer <key> (prefixo sk-local-), PBKDF2-SHA256"],
        ["OAuth2 SSO", "Google, GitHub"],
        ["Enterprise SSO", "Azure AD, Okta, SAML 2.0"],
        ["Endpoint Keys", "Para agent-as-API deployments"],
    ]
)

# ============================================================
#  6. SERVIÇOS
# ============================================================
add_heading("6. Serviços (Business Logic)", 1)

add_paragraph("A camada de serviços em control_plane/app/services/ contém ~96 módulos:")

add_table(
    ["Serviço", "Arquivo", "Descrição"],
    [
        ["InferenceProxy", "inference_proxy.py (1045 linhas)", "Proxy principal: forward, retry, circuit breaker, "
         "streaming, tradução Ollama, detecção anti-loop, contagem de tokens"],
        ["QueueManager", "queue_manager.py (197 linhas)", "Fila prioritária de 4 tiers (admin/premium/basic/free)"],
        ["BackendSlotManager", "backend_slot_manager.py", "Slots de concorrência por backend (SELECT FOR UPDATE)"],
        ["CircuitBreaker", "circuit_breaker.py", "Threshold de falha + timeout de recuperação"],
        ["RateLimiter", "security/rate_limit.py", "Token bucket via Redis"],
        ["Billing Core", "billing/core.py", "Engine de precificação, resolução de planos"],
        ["Billing Scheduler", "billing_scheduler.py", "Geração mensal de faturas (60 min)"],
        ["Wallet Service", "billing/wallet_service.py", "Gestão de carteiras digitais"],
        ["RAG Processor", "rag_processor.py", "Chunking, embedding, retrieval"],
        ["Auth Service", "auth.py", "Autenticação admin + client"],
        ["Admin RBAC", "admin_rbac.py", "RBAC em banco de dados"],
        ["Agent Platform", "agents/ (50+ arquivos)", "Execução, sessões, ferramentas, workflows, memória"],
        ["Commercial Services", "routing/, inference/, models/", "Roteamento, federação, QoS, atestação"],
        ["Operations Services", "operations/", "Compliance, SOC2, caos, correlação"],
        ["Security Services", "security/", "Atestação, monitoramento de segurança"],
    ]
)

# ============================================================
#  7. FRONTEND
# ============================================================
add_heading("7. Frontend", 1)

add_paragraph(
    "O frontend consiste em duas SPAs (Single Page Applications) separadas, "
    "ambas construídas com React 19 + TypeScript 6 + Vite 8 + Tailwind CSS v4."
)

add_heading("7.1 Admin Dashboard", 2)
add_item("Localização", "frontend/admin/")
add_item("Features", "Dashboard, Clients, Models, Backends, Billing, Usage, RBAC, "
         "Agentes (Studio, MCP, Analytics, Approvals, Deployments, Knowledge Graph, Optimization), "
         "Operações, Compliance, Observabilidade, Performance, Enterprise, Multi-Cluster, Federação, Caos")
add_item("State Management", "Zustand + TanStack React Query")
add_item("HTTP Client", "Axios com interceptors")
add_item("Testes", "Vitest + Playwright + Storybook 10")
add_item("Rotas", "50+ rotas em 9 seções, react-router-dom v7")

add_heading("7.2 Client Portal", 2)
add_item("Localização", "frontend/client/")
add_item("Features", "Dashboard de uso (Recharts), Chat com agente (WebSocket streaming), "
         "Documentos RAG, API Keys, Invoices, Wallet (PIX), Webhooks, Branding, Notificações Push, Settings")
add_item("PWA", "Service worker, offline fallback, push notifications, manifest.webmanifest")
add_item("State Management", "React hooks (useState, useRef)")
add_item("HTTP Client", "Native fetch")

# ============================================================
#  8. SDKs
# ============================================================
add_heading("8. SDKs Multi-Linguagem", 1)

add_item("Python SDK", "sdk/python/kleberai/ v0.2.0 - 16 sub-APIs + CLI agentctl")
add_item("Node.js SDK", "sdk/node/ - TypeScript, ESM, compila com tsc")
add_item("Go SDK", "sdk/go/ - Go 1.22, 15 API sub-services")

add_paragraph("Todos os SDKs fornecem clientes para: Agents, Memory, Tools, Marketplace, Studio, "
              "Workflows, Knowledge Graph, Sessions, MCP, Deployments, RAG, Admin, System.")

# ============================================================
#  9. TESTES
# ============================================================
add_heading("9. Testes", 1)

add_item("Framework", "pytest (asyncio_mode=auto)")
add_item("Cobertura Mínima", "75% (pytest-cov)")
add_item("Total de Testes", "~720+ (647 em tests/ + 73 em control_plane/tests/)")
add_item("Testes E2E", "Playwright + HTTPX async client")
add_item("Testes de Caos", "Resiliência com injeção de falhas")
add_item("Testes de Carga", "k6 + Python scale test")
add_item("Property-based", "Hypothesis")
add_item("Markers", "quick, slow, release, chaos, k8s, integration, local_llm")

add_paragraph("Organização dos testes:")
add_table(
    ["Diretório", "Foco"],
    [
        ["tests/api/", "Testes de endpoint"],
        ["tests/architecture/", "Arquitetura, dependências"],
        ["tests/chaos/", "Resiliência e caos"],
        ["tests/compliance/", "Conformidade (SOC2/ISO27001/GDPR)"],
        ["tests/contracts/", "Contratos entre contextos"],
        ["tests/docs/", "Validação de documentação"],
        ["tests/e2e/", "Testes end-to-end"],
        ["tests/e2e-playwright/", "Testes de browser"],
        ["tests/governance/", "Políticas de governança"],
        ["tests/kubernetes/", "Deploy K8s"],
        ["tests/llm_harness/", "LLM Harness (69 testes)"],
        ["tests/load/", "Testes de carga"],
        ["tests/operations/", "Fases 69-82 (144 testes)"],
        ["tests/performance/", "Baselines de performance"],
        ["tests/security/", "Segurança (sandbox, jailbreak)"],
    ]
)

# ============================================================
#  10. DEVOPS / DOCKER
# ============================================================
add_heading("10. Docker e Implantação", 1)

add_heading("10.1 Serviços Docker Compose", 2)
add_table(
    ["Serviço", "Imagem", "Porta", "Perfil"],
    [
        ["postgres", "postgres:16-alpine", "5432", "sempre"],
        ["redis", "redis:7-alpine", "6379", "sempre"],
        ["control-plane", "Dockerfile custom", "18080", "sempre"],
        ["control-plane-worker", "Dockerfile custom", "-", "sempre"],
        ["rag-worker", "Dockerfile custom", "-", "sempre"],
        ["data-plane-gemma", "Dockerfile custom", "8081", "sempre"],
        ["data-plane-ollama", "ollama/ollama:0.9.5", "11434", "ollama"],
        ["data-plane-mock", "Dockerfile custom", "8081", "fallback-test"],
        ["agent-worker", "Dockerfile custom", "-", "agentic"],
        ["prometheus", "prom/prometheus:v2.53.4", "9090", "observability"],
        ["grafana", "grafana/grafana:11.1.4", "3001", "observability"],
        ["pocket-tts", "Dockerfile custom", "8000", "sempre"],
        ["otel-collector", "otel/opentelemetry-collector-contrib:0.118.0", "4317", "observability"],
        ["loki", "grafana/loki:3.4.2", "3100", "observability"],
        ["promtail", "grafana/promtail:3.4.2", "-", "observability"],
        ["tempo", "grafana/tempo:2.7.1", "3200", "observability"],
    ]
)

add_heading("10.2 Kubernetes / Helm", 2)
add_item("Helm Chart", "deploy/helm/llm-inference-stack/")
add_item("Manifests K8s", "deploy/kubernetes/ (deployments, services, PVCs, CRDs)")
add_item("Operador K8s", "operator/main.py (Kopf framework) - reconcilia 5 CRDs")
add_item("CRDs", "LLMWorker, LLMInferenceStack, LLMModelRuntime, LLMProvider, LLMTenant")

add_heading("10.3 CI/CD (GitHub Actions)", 2)
add_item("Workflows", "14 workflows: CI, Security, Compliance, Chaos, Docker Build, "
         "Deploy K8s, Deploy Appliance, Deploy Pilot, LLM Harness, Agent Evals, "
         "Release Validation, Docs Validation, K8s Validation, Storybook Docs")

# ============================================================
#  11. PLATAFORMA DE AGENTES
# ============================================================
add_heading("11. Plataforma de Agentes", 1)

add_paragraph(
    "A plataforma possui um runtime completo de agentes com execução governada, "
    "memória, ferramentas, protocolo MCP, grafo de conhecimento e orquestração."
)

add_table(
    ["Componente", "Descrição"],
    [
        ["Agent Registry", "Registro CRUD de definições de agentes"],
        ["Agent Runtime", "Plano de execução com sandbox de ferramentas"],
        ["Agent Executor", "Execução de tarefas com portões de aprovação"],
        ["Agent Memory", "Memória de trabalho, longo prazo, semântica, cognitiva"],
        ["Agent Tools", "Registro de ferramentas, síntese, protocolo MCP, HTTP/DB/Shell"],
        ["Agent Knowledge Graph", "RAG em grafo com pgvector/pgRouting"],
        ["Agent Studio", "Autoria visual de fluxos (GA-gated)"],
        ["Agent IAM", "Service principals, tokens delegados, OAuth"],
        ["Agent Events", "Triggers event-driven (cron, pub/sub, webhooks)"],
        ["Agent Workflows", "Orquestração stateful de workflows"],
        ["Agent CI/CD", "Experimentos de otimização, torneios, promoção canário"],
        ["Agent Wallet", "Sistema de carteira para gastos de agentes"],
        ["Agent Eval", "Framework de avaliação com portões de promoção"],
        ["Agent Deployments", "Agent-as-API com keys e SLA"],
        ["Agent Observability", "Tracing, telemetria, backpressure"],
        ["Agent A2A", "Protocolo Agent-to-Agent"],
    ]
)

# ============================================================
#  12. MONITORAMENTO
# ============================================================
add_heading("12. Monitoramento e Observabilidade", 1)

add_table(
    ["Ferramenta", "Função"],
    [
        ["Prometheus", "Coleta de métricas"],
        ["Grafana", "Dashboards (9 pré-configurados: agentic overview, approvals, costs, "
         "memory, tools, GPU capacity, platform overview, runtime nodes, SLO error budget)"],
        ["OpenTelemetry", "Coletor de traces distribuídos"],
        ["Loki + Promtail", "Agregação de logs"],
        ["Tempo", "Armazenamento de traces"],
        ["Alert Rules", "Regras de alerta configuradas"],
    ]
)

# ============================================================
#  13. CONFIGURAÇÕES
# ============================================================
add_heading("13. Configurações", 1)

add_paragraph("O sistema possui 25+ arquivos de configuração em config/:")
add_table(
    ["Arquivo", "Descrição"],
    [
        ["config/feature-flags.yaml", "Definições de feature flags"],
        ["config/api-surface.yaml", "Superfície da API (8016 linhas)"],
        ["config/supported-surface.yaml", "Tiers de suporte (Production Core, Beta, Experimental, etc.)"],
        ["config/deployment-modes.yaml", "Modos de deploy"],
        ["config/platform-profiles/", "5 perfis (appliance, agentic-pilot, agentic-production, etc.)"],
        ["config/runtime-profiles/", "5 perfis de runtime"],
        ["config/agent-policies/default.yaml", "Políticas padrão de agentes"],
        ["config/pricing.example.json", "Exemplos de precificação"],
    ]
)

add_paragraph("O arquivo .env.example possui 637 linhas com todas as variáveis de ambiente "
              "organizadas em seções: geral, custos, admin, URLs, banco de dados, Redis, "
              "data plane, timeouts, limites de tokens, circuit breaker, cache, PKI/attestation, "
              "enterprise runtime, agente (200+ vars), operador, pagamento, demo, modelo, "
              "abuse detection, tokenizer, compliance, RAG, provider credentials, fases comerciais.")

# ============================================================
#  14. COMERCIAL E CONTRATOS
# ============================================================
add_heading("14. Comercial e Contratos", 1)

add_item("contracts/", "Templates de SOW, Service Agreement, Support Terms, Acceptance Criteria")
add_item("proposals/", "Templates de proposta comercial/técnica, one-pager")
add_item("commercial/templates/", "SOW Enterprise, SUPPORT_TERMS, DPB, SECURITY_APPENDIX")
add_item("commercial/checklists/", "Checklists: pré-instalação, instalação, handover, validação, treinamento, pós-go-live")
add_item("commercial/packages/", "Definições de pacotes enterprise")

# ============================================================
#  15. SEGURANÇA
# ============================================================
add_heading("15. Segurança e Compliance", 1)

add_item("PKI", "CA certificate/key, CRL em data/pki/")
add_item("Recibos Criptográficos", "Para cada inferência e mudança de configuração")
add_item("Logs Determinísticos", "Eventos de auditoria imutáveis")
add_item("Controles de Criptografia", "Por tenant")
add_item("Airgap Soberano", "Governança de isolamento")
add_item("Integridade de Modelos", "Monitoramento em runtime")
add_item("Detecção de Abuso", "Rate limiting, inspeção de payload")
add_item("Secrets Scanning", "Pre-commit hooks")
add_item("RBAC", "Controle de acesso admin baseado em papéis/permissões")
add_item("Compliance", "Evidências SOC2/ISO27001/GDPR, risk register, policy enforcement")

# ============================================================
#  16. SCRIPTS E FERRAMENTAS
# ============================================================
add_heading("16. Scripts e Ferramentas", 1)

add_item("scripts/", "~518 scripts operacionais (deploy, validation, security, compliance, "
         "chaos, agent ops, backup/restore, commercial, testing, LLM harness)")
add_item("tools/", "Public verifier tooling")
add_item("chaos/", "Cenários de caos para CI (ex: provider_timeout.json)")
add_item("examples/", "Integrações: Python, curl, LangChain, n8n, Open WebUI, Node, plugins, anythingllm")

# ============================================================
#  17. FASES DE VALIDAÇÃO
# ============================================================
add_heading("17. Fases de Validação (Arquitetura 69-82)", 1)

add_paragraph("A plataforma evolui através de fases de validação arquitetural:")
add_table(
    ["Fase", "Descrição"],
    [
        ["P69", "Failure Forecasting - Previsão de falhas"],
        ["P70", "Correlation Engine - Motor de correlação"],
        ["P71", "Remediation Planning - Planejamento de remediação"],
        ["P72", "Remediation Execution - Execução de remediação"],
        ["P73", "Adapter Sandbox - Sandbox de adaptadores"],
        ["P74", "Signed Adapter Registry - Registro assinado de adaptadores"],
        ["P75", "Adapter Promotion - Promoção de adaptadores"],
        ["P76", "Attestation Framework - Framework de atestação"],
        ["P77", "Federation Sync - Sincronização de federação"],
        ["P78", "Compatibility Contracts - Contratos de compatibilidade"],
        ["P79", "Plugin ABI - Interface binária de plugins"],
        ["P80", "Plugin Supply Chain - Supply chain de plugins"],
        ["P81", "Reproducible Builds - Builds reproduzíveis"],
        ["P82", "Platform Sustainability - Sustentabilidade da plataforma"],
    ]
)

# ============================================================
#  18. RELEASES
# ============================================================
add_heading("18. Histórico de Releases", 1)

add_paragraph("O diretório releases/ contém 21 versões arquivadas:")
versions = [
    "v1.4.3-local-hardening", "v2.0.0-core", "v2.0.1", "v2.0.2", "v2.0.3",
    "v2.0.4", "v2.0.5", "v2.0.6", "v2.0.7",
    "v2.x-agentic-ux-completion", "v2.x-agentic-critical-gaps",
    "v2.x-agentic-platform-gap-closure", "v2.x-agentic-evolutionary-intelligence",
    "v2.x-agentic-production-trust-hardening", "v2.x-agentic-platform-complete-hardening",
    "(outras na sequência)"
]
add_paragraph(" • ".join(versions))

# ============================================================
#  19. LICENÇA
# ============================================================
# (No LICENSE file found, but SECURITY.md and CONTRIBUTING.md exist)

# ============================================================
#  FOOTER
# ============================================================
doc.add_page_break()
add_heading("Apêndice: Comandos Úteis", 1)

commands = [
    ("docker compose up -d", "Iniciar todos os serviços"),
    ("make up", "Subir a stack via Makefile"),
    ("make down", "Parar a stack"),
    ("make test", "Rodar testes de regressão"),
    ("make test-smoke", "Testes smoke rápidos"),
    ("make validate-architecture-smoke", "Validar arquitetura (fases 69-82)"),
    ("make agentic-up", "Ativar modo agentes"),
    ("make agentic-readiness", "Verificar readiness agentic"),
    ("make install-local", "Instalação local completa"),
    ("make health", "Health check"),
    ("make logs", "Ver logs"),
    ("make backup", "Fazer backup"),
    ("make restore", "Restaurar backup"),
    ("make security-report", "Relatório de segurança"),
    ("make compliance-check", "Verificação de compliance"),
]

add_table(["Comando", "Descrição"], commands)

doc.add_paragraph()
footer = doc.add_paragraph()
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = footer.add_run("--- Fim do Relatório ---")
run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
run.font.size = Pt(9)

output_path = "/home/kleber/llm-inference-stack/reports/relatorio_sistema_llm_inference_stack.docx"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
doc.save(output_path)
print(f"Relatório salvo em: {output_path}")
