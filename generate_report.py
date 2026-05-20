#!/usr/bin/env python3
"""Generate comprehensive system report in .docx format."""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
import datetime

doc = Document()

# -- Style setup --
style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(10)

for level in range(1, 4):
    hs = doc.styles[f'Heading {level}']
    hs.font.color.rgb = RGBColor(0x1a, 0x3c, 0x6e)

def add_table(headers, rows, col_widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    hdr = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        cell.text = h
        for p in cell.paragraphs:
            p.style = doc.styles['Normal']
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(9)
    for row_data in rows:
        row = table.add_row()
        for i, val in enumerate(row_data):
            row.cells[i].text = str(val)
            for p in row.cells[i].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    return table

# ============================================================
# TITLE PAGE
# ============================================================
doc.add_paragraph()
doc.add_paragraph()
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run('LLM Inference Stack')
run.bold = True
run.font.size = Pt(28)
run.font.color.rgb = RGBColor(0x1a, 0x3c, 0x6e)

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run('Relatório Detalhado do Sistema')
run.font.size = Pt(18)
run.font.color.rgb = RGBColor(0x4a, 0x4a, 0x4a)

doc.add_paragraph()
info = doc.add_paragraph()
info.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = info.add_run(f'Versão: v1.9.4-enterprise-runtime\nBuild: v1.9.3-stabilization-hardening\nData: {datetime.date.today().strftime("%d/%m/%Y")}\nBranch: release/v1.8.3')
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

doc.add_paragraph()
desc = doc.add_paragraph()
desc.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = desc.add_run('Plataforma soberana de inferência AI, offline-first, determinística.\nMulti-tenant, multi-provider, white-label ready.')
run.font.size = Pt(11)
run.italic = True

doc.add_page_break()

# ============================================================
# TABLE OF CONTENTS (placeholder)
# ============================================================
doc.add_heading('Sumário', level=1)
toc_items = [
    '1. Visão Geral do Sistema',
    '2. Identidade e Versionamento',
    '3. Arquitetura do Sistema',
    '4. Estrutura de Diretórios',
    '5. Control Plane (Backend)',
    '6. Data Plane (Inferência)',
    '7. Frontend (Admin Dashboard)',
    '8. SDKs (Python e Node.js)',
    '9. Infraestrutura e Deploy',
    '10. Docker e Containers',
    '11. Kubernetes e Helm',
    '12. CI/CD Pipelines',
    '13. Monitoramento e Observabilidade',
    '14. Segurança',
    '15. Compliance (SOC 2 / ISO 27001)',
    '16. Chaos Engineering',
    '17. Governança e Políticas',
    '18. Testes',
    '19. Documentação',
    '20. Scripts Operacionais',
    '21. Contratos e Propostas Comerciais',
    '22. Ferramentas (Tools)',
    '23. Estatísticas do Código',
    '24. Roadmap e Fases',
]
for item in toc_items:
    p = doc.add_paragraph(item)
    p.paragraph_format.space_after = Pt(2)

doc.add_page_break()

# ============================================================
# 1. VISÃO GERAL
# ============================================================
doc.add_heading('1. Visão Geral do Sistema', level=1)
doc.add_paragraph(
    'O LLM Inference Stack é uma plataforma soberana de inferência de LLMs (Large Language Models) '
    'projetada para operar de forma completamente offline, sem dependência de serviços cloud. '
    'A plataforma segue os princípios de determinismo, replay-safety, offline-first, soberania do operador '
    'e governança advisory-first.'
)
doc.add_paragraph(
    'A arquitetura é baseada em Control Plane / Data Plane, com o Control Plane (FastAPI/Python) '
    'gerenciando autenticação, roteamento, billing, RAG e toda a lógica de negócios, enquanto o '
    'Data Plane (llama.cpp com CUDA) executa a inferência real dos modelos GGUF com aceleração GPU.'
)

doc.add_heading('Princípios de Design', level=2)
principles = [
    ('Determinístico', 'Cada operação produz outputs reproduzíveis e verificáveis. Logs de eventos, receipts e decisões de governança são reprodutíveis offline.'),
    ('Replay-Safe', 'Todas as transições de estado podem ser reproduzidas a partir de logs de eventos sem efeitos colaterais.'),
    ('Offline-First', 'A plataforma opera totalmente sem conectividade com a internet. Providers cloud são opcionais, nunca obrigatórios.'),
    ('Soberano', 'Operadores retêm controle total sobre dados, modelos, políticas e execução. Sem vendor lock-in.'),
    ('Advisory-First', 'Validação, política e governança rodam em modo advisory/dry-run por padrão. Enforcement é explícito e controlado pelo operador.'),
]
add_table(['Princípio', 'Descrição'], principles)

doc.add_heading('Modos de Deploy', level=2)
modes = [
    ('Appliance (Local/Offline)', 'Deploy local em hardware dedicado, operação totalmente desconectada'),
    ('SaaS', 'Modo multi-tenant para oferecer como serviço gerenciado'),
    ('Managed Control Plane', 'Control plane gerenciado para múltiplos appliances'),
    ('Hybrid', 'Combinação de local + cloud com failover automático'),
]
add_table(['Modo', 'Descrição'], modes)

doc.add_page_break()

# ============================================================
# 2. IDENTIDADE
# ============================================================
doc.add_heading('2. Identidade e Versionamento', level=1)
identity = [
    ('Nome', 'LLM Inference Stack (Local AI Appliance)'),
    ('VERSION', 'v1.9.3-stabilization-hardening'),
    ('Build Atual', 'v1.9.4-enterprise-runtime'),
    ('Helm Chart appVersion', '1.9.3'),
    ('Branch Atual', 'release/v1.8.3'),
    ('Linguagem Principal', 'Python (FastAPI)'),
    ('Framework Frontend', 'React + TypeScript (Vite)'),
    ('Banco de Dados', 'PostgreSQL 16 + Redis 7'),
    ('Data Plane', 'llama.cpp (CUDA 12.6) / Ollama'),
    ('Branding SDK', 'Kleber AI'),
]
add_table(['Campo', 'Valor'], identity)

doc.add_heading('Histórico de Releases', level=2)
doc.add_paragraph('O projeto possui 48 releases documentados, desde v1.0.0-beta até v1.9.4-enterprise-runtime.')
releases = [
    ('v1.9.4', 'enterprise-runtime', 'Enterprise Runtime'),
    ('v1.9.3', 'stabilization-hardening', 'Stabilization & Hardening'),
    ('v1.9.5', 'operational-experience', 'Operational Experience'),
    ('v1.9.6', 'ci-chaos', 'CI & Chaos Engineering'),
    ('v1.9.7', 'compliance-readiness', 'Compliance Readiness'),
    ('v1.8.1', 'real-provider-validation', 'Real Provider Validation'),
    ('v1.7.0', 'local-ai-appliance', 'Local AI Appliance'),
    ('v1.4.3', 'local-hardening', 'Local Hardening'),
]
add_table(['Versão', 'Tag', 'Descrição'], releases)

doc.add_page_break()

# ============================================================
# 3. ARQUITETURA
# ============================================================
doc.add_heading('3. Arquitetura do Sistema', level=1)
doc.add_paragraph(
    'O sistema segue uma arquitetura hub-and-spoke com separação clara entre Control Plane e Data Plane.'
)

doc.add_heading('Componentes Principais', level=2)
components = [
    ('Control Plane', 'FastAPI (Python 3.12)', 'API OpenAI-compatível, autenticação, billing, roteamento, RAG, governança'),
    ('Data Plane', 'llama.cpp + CUDA', 'Inferência de modelos GGUF com aceleração GPU'),
    ('Mock Data Plane', 'FastAPI', 'Backend mock para testes sem GPU'),
    ('PostgreSQL 16', 'Banco de Dados', 'Armazenamento de estado, multi-tenant'),
    ('Redis 7', 'Cache/Fila', 'Rate limiting, cache de respostas, filas de jobs'),
    ('Nginx / Caddy', 'Reverse Proxy', 'TLS termination, roteamento'),
    ('Prometheus', 'Métricas', 'Coleta de métricas do sistema'),
    ('Grafana', 'Dashboards', 'Visualização de métricas e SLOs'),
    ('pocket-tts', 'Text-to-Speech', 'Serviço de síntese de fala'),
    ('Kopf Operator', 'Kubernetes', 'Operador K8s para CRDs customizadas'),
]
add_table(['Componente', 'Tecnologia', 'Função'], components)

doc.add_heading('Contextos Delimitados (Bounded Contexts)', level=2)
contexts = [
    'core_runtime', 'data_governance', 'disaster_recovery', 'federation',
    'financial', 'governance', 'observability', 'operations',
    'plugin_runtime', 'runtime', 'security', 'sovereign',
    'supply_chain', 'trust'
]
for i, ctx in enumerate(contexts):
    doc.add_paragraph(f'{i+1}. {ctx}', style='List Number')

doc.add_page_break()

# ============================================================
# 4. ESTRUTURA DE DIRETÓRIOS
# ============================================================
doc.add_heading('4. Estrutura de Diretórios', level=1)
doc.add_paragraph('O repositório contém 46 diretórios de nível raiz e 47 arquivos de nível raiz.')

directories = [
    ('control_plane/', 'Aplicação principal - FastAPI Control Plane'),
    ('data_plane_mock/', 'Mock do Data Plane para testes'),
    ('frontend/', 'Admin Dashboard (React + TypeScript + Vite)'),
    ('sdk/', 'Client SDKs (Python e Node.js)'),
    ('tools/', 'CLI tools (Public Verifier)'),
    ('operator/', 'Kubernetes Operator (kopf)'),
    ('docker/', 'Dockerfiles e configs de todos os serviços'),
    ('deploy/', 'Deploy configs (Kubernetes, Helm, automação)'),
    ('monitoring/', 'Prometheus, Grafana, dashboards, alertas'),
    ('compliance/', 'Framework SOC 2 / ISO 27001'),
    ('chaos/', 'Chaos Engineering (cenários, experimentos, reports)'),
    ('docs/', 'Documentação (140+ arquivos, 25+ subdiretórios)'),
    ('tests/', 'Suite de testes (700+ arquivos)'),
    ('scripts/', 'Scripts operacionais (385+ scripts)'),
    ('config/', 'Exemplos de configuração (branding, pricing, routing)'),
    ('contracts/', 'Templates de contratos legais (SOW, SLA)'),
    ('proposals/', 'Templates de propostas comerciais'),
    ('commercial/', 'Templates e checklists comerciais'),
    ('artifacts/', 'Relatórios gerados (68 subdiretórios)'),
    ('releases/', 'Manifests de release (20 versões)'),
    ('examples/', 'Exemplos de integração (curl, Python, Node.js, LangChain)'),
    ('models/', 'Armazenamento de modelos GGUF'),
    ('data/', 'Dados runtime (PKI, plugins, RAG uploads)'),
    ('demo/ / demo-pack/', 'Materiais de demonstração'),
    ('bin/', 'Binários (llama-server)'),
]
add_table(['Diretório', 'Propósito'], directories)

doc.add_page_break()

# ============================================================
# 5. CONTROL PLANE
# ============================================================
doc.add_heading('5. Control Plane (Backend)', level=1)
doc.add_paragraph(
    'O Control Plane é o coração do sistema — uma aplicação FastAPI que gerencia clientes, modelos, '
    'billing, roteamento e faz proxy de requisições de inferência para o Data Plane.'
)

doc.add_heading('Core Layer', level=2)
core_files = [
    ('config.py', '~1000 linhas', 'Classe Settings com 300+ variáveis de ambiente'),
    ('security.py', '', 'Geração de API keys (sk-local-...), PBKDF2-SHA256'),
    ('logging.py', '', 'Logging JSON estruturado com correlation ID'),
    ('metrics.py', '', 'Contadores e histogramas Prometheus'),
    ('request_context.py', '', 'Context-var para tracking de correlation ID'),
    ('runtime_security.py', '', 'Validação de startup: tokens admin, CORS'),
    ('time.py', '', 'Utilitários de tempo UTC'),
]
add_table(['Arquivo', 'Tamanho', 'Função'], core_files)

doc.add_heading('Camada de ORM Models (120+ modelos)', level=2)
doc.add_paragraph('O projeto define mais de 120 modelos SQLAlchemy organizados em:')
model_groups = [
    ('Core', 'client, api_key, billing_plan, billing_invoice, pricing_rule, usage_record, quota_counter, request_log, model_registry, inference_backend, model_backend_route'),
    ('Security', 'security_event, abuse_event, abuse_action, admin_rbac, admin_action_log, security_pki'),
    ('Financial', 'customer_payment, payment_topup, ai_wallet, request_financial'),
    ('RAG', 'rag_document, rag_document_chunk, rag_collection, rag_usage_event, commercial_rag_vault'),
    ('Commercial (50+)', 'routing, node_heartbeat, cluster_registry, global_traffic, qos_tier, revenue_forecast, compliance, governance, encryption, sovereign, model_supply_chain, agents, workflows, runtime_fabric, predictive_aiops, confidential_runtime'),
    ('Operations (20+)', 'adapter_sandbox, adapter_registry, attestation_framework, federation_sync, compatibility_contracts, plugin_runtime, reproducible_builds, correlation, failure_signals, remediation, chaos, disaster_recovery'),
    ('Governance', 'policy_engine, data_governance, human_governance, release_baseline'),
    ('Runtime', 'distributed_runtime, gpu_orchestration'),
    ('Plugins', 'marketplace'),
]
add_table(['Grupo', 'Modelos'], model_groups)

doc.add_heading('API Endpoints (100+ routers)', level=2)
api_groups = [
    ('Client-Facing', '/v1/chat/completions, /v1/completions, /v1/embeddings, /v1/models, /v1/responses'),
    ('Public', 'Plan listing, client signup, health'),
    ('Portal', 'Client self-service: usage, invoices, profile'),
    ('Admin', 'CRUD completo para clients, backends, models, billing, API keys, routes'),
    ('Admin RBAC', 'Gestão de usuários, roles, permissões'),
    ('Commercial (50+)', 'Routing, guardrails, federation, global traffic, QoS, compliance, encryption, sovereign, agents, workflows, AIOps'),
    ('Operations (15+)', 'Correlation, remediation, adapters, attestation, federation sync, plugins, reproducible builds'),
    ('RAG', 'Upload, query, enterprise vault'),
    ('Payments', 'Top-up, wallet'),
    ('TTS', 'Text-to-speech endpoints'),
]
add_table(['Grupo de API', 'Endpoints Principais'], api_groups)

doc.add_heading('Services Layer (40+ subdiretórios)', level=2)
services = [
    ('auth.py', 'Autenticação de API keys, RBAC admin com hierarquia de roles'),
    ('inference_proxy.py', 'HTTP proxy para data plane com circuit breaker, queue, fallback, streaming'),
    ('quota.py', 'Enforcement de cota de tokens (limites diários/mensais)'),
    ('rate_limit.py', 'Rate limiting por cliente e IP (Redis sliding window)'),
    ('circuit_breaker.py', 'Circuit breaker para falhas de backend'),
    ('queue_manager.py', 'Fila de prioridade com limites por tier'),
    ('response_cache.py', 'Cache exato de respostas (Redis)'),
    ('security_monitor.py', 'Detecção de eventos de segurança'),
    ('model_policy.py', 'Resolução de modelos, ordem de roteamento'),
    ('tokenizer_service.py', 'Contagem de tokens (auto/tiktoken/local)'),
    ('billing/', 'Invoice generation, pricing engine, wallet, guardrails, reconciliation, anomaly detection'),
    ('routing/', 'Analytics, federation, heartbeat, infra adapters (K8s, Nomad, Proxmox)'),
    ('governance/', 'Policy engine, data governance, human governance, release engineering'),
    ('operations/', 'Correlation, forecasting, remediation, adapters, attestation, federation, plugins, reproducible builds, DR'),
    ('agents/', 'Agent governance, tool policy, execution receipts'),
    ('workflows/', 'Workflow engine determinístico com checkpoints e replay'),
]
add_table(['Service', 'Função'], services)

doc.add_page_break()

# ============================================================
# 6. DATA PLANE
# ============================================================
doc.add_heading('6. Data Plane (Inferência)', level=1)
doc.add_paragraph(
    'O Data Plane executa a inferência real dos modelos de linguagem. '
    'Utiliza llama.cpp compilado com CUDA 12.6 para aceleração GPU, servindo modelos no formato GGUF.'
)

doc.add_heading('Configuração do Data Plane', level=2)
dp_config = [
    ('MODEL_FILE', 'Caminho do modelo GGUF'),
    ('LLAMA_CTX_SIZE', 'Tamanho do contexto'),
    ('LLAMA_N_GPU_LAYERS', 'Camadas delegadas à GPU'),
    ('LLAMA_THREADS', 'Threads de CPU'),
    ('LLAMA_BATCH_SIZE', 'Tamanho do batch'),
    ('LLAMA_PARALLEL', 'Requisições paralelas'),
    ('LLAMA_CONT_BATCHING', 'Batching contínuo'),
    ('LLAMA_FLASH_ATTN', 'Flash attention'),
]
add_table(['Variável', 'Descrição'], dp_config)

doc.add_heading('Mock Data Plane', level=2)
doc.add_paragraph(
    'Para testes sem GPU, o projeto inclui um mock data plane (FastAPI) que responde '
    'a /health, /v1/models e /v1/chat/completions com respostas hardcoded.'
)

doc.add_page_break()

# ============================================================
# 7. FRONTEND
# ============================================================
doc.add_heading('7. Frontend (Admin Dashboard)', level=1)
doc.add_paragraph(
    'O projeto possui duas interfaces de administração:'
)

doc.add_heading('Frontend Moderno (React)', level=2)
doc.add_paragraph(
    'Localizado em frontend/admin/, é uma aplicação React + TypeScript construída com Vite. '
    'Utiliza Zustand para gerenciamento de estado e Axios para comunicação com a API. '
    'O token de administração é injetado automaticamente via interceptor.'
)

doc.add_heading('Frontend Legado (Static HTML/JS)', level=2)
doc.add_paragraph(
    'O Control Plane serve interfaces HTML/JS estáticas a partir de control_plane/app/static/: '
    'admin (clients, backends, models, billing, settings, security, RAG, usage, reports), '
    'portal (client self-service), www (public website).'
)

doc.add_page_break()

# ============================================================
# 8. SDKs
# ============================================================
doc.add_heading('8. SDKs (Python e Node.js)', level=1)
doc.add_paragraph('O projeto fornece SDKs oficiais para Python e Node.js com a marca "Kleber AI".')

sdk_details = [
    ('Python', 'sdk/python/kleberai/', 'httpx', 'chat(), models(), embeddings(), rag_query()'),
    ('Node.js', 'sdk/node/', 'fetch API', 'chat(), models(), embeddings(), rag_query()'),
]
add_table(['Linguagem', 'Localização', 'HTTP Client', 'Métodos'], sdk_details)

doc.add_page_break()

# ============================================================
# 9. INFRAESTRUTURA
# ============================================================
doc.add_heading('9. Infraestrutura e Deploy', level=1)

doc.add_heading('Opções de Deploy', level=2)
deploy_options = [
    ('Docker Compose', 'Desenvolvimento e produção local', 'Ativo'),
    ('Kubernetes + Helm', 'Produção em cluster', 'Manifests prontos'),
    ('Kubernetes Operator', 'Gestão declarativa via CRDs', 'Scaffold/SPI'),
    ('Automação', 'Scripts de deploy com audit trail', '6 scripts'),
]
add_table(['Método', 'Uso', 'Status'], deploy_options)

doc.add_heading('Custom Resource Definitions (CRDs)', level=2)
crds = [
    ('LLMInferenceStack', 'Recurso top-level do stack com spec para replicas, demoMode, image'),
    ('LLMModelRuntime', 'Runtime de modelo com modelFile, image, configuração GPU'),
    ('LLMProvider', 'Configuração de provider externo com type e apiKeySecretRef'),
    ('LLMTenant', 'Recurso de tenant com name e quota'),
]
add_table(['CRD', 'Descrição'], crds)

doc.add_page_break()

# ============================================================
# 10. DOCKER
# ============================================================
doc.add_heading('10. Docker e Containers', level=1)

dockerfiles = [
    ('control-plane/Dockerfile', 'Python 3.12-slim, instala deps, roda Alembic + uvicorn na porta 8080'),
    ('data-plane/Dockerfile', 'Multi-stage: NVIDIA CUDA 12.6, compila llama.cpp, roda llama-server na porta 8081'),
    ('data-plane-mock/Dockerfile', 'FastAPI mock para testes sem GPU'),
    ('reverse-proxy/Dockerfile', 'Nginx 1.27-alpine com configs HTTP e TLS'),
    ('pocket-tts/Dockerfile', 'Python 3.12-slim com pocket-tts para síntese de fala'),
    ('caddy/Caddyfile', 'Caddy 2.10 com TLS automático (Let\'s Encrypt)'),
]
add_table(['Dockerfile', 'Descrição'], dockerfiles)

doc.add_heading('Serviços Docker Compose', level=2)
compose_services = [
    ('postgres', 'PostgreSQL 16-alpine', 'control_net'),
    ('redis', 'Redis 7-alpine', 'control_net'),
    ('data-plane-gemma', 'llama.cpp + GPU NVIDIA', 'data_net (interna)'),
    ('data-plane-ollama', 'Ollama 0.9.5 (profile: ollama)', 'data_net'),
    ('data-plane-mock', 'Mock backend (profile: fallback-test)', 'data_net'),
    ('control-plane', 'FastAPI API server', 'control_net'),
    ('control-plane-worker', 'Worker de geração assíncrona', 'control_net'),
    ('rag-worker', 'Worker de processamento RAG', 'control_net'),
    ('prometheus', 'Métricas (profile: observability)', 'control_net'),
    ('grafana', 'Dashboards (profile: observability)', 'control_net'),
    ('pocket-tts', 'Text-to-speech', 'control_net'),
]
add_table(['Serviço', 'Descrição', 'Rede'], compose_services)

doc.add_page_break()

# ============================================================
# 11. KUBERNETES
# ============================================================
doc.add_heading('11. Kubernetes e Helm', level=1)

doc.add_heading('Manifests Kubernetes', level=2)
k8s_resources = [
    ('deployments.yaml', 'Deployments para postgres, redis, data-plane, control-plane, workers'),
    ('services.yaml', 'ClusterIP services para postgres:5432, redis:6379, data-plane:8081, control-plane:8080'),
    ('config.yaml', 'ConfigMap + Secret com URLs de DB/Redis, demo mode'),
    ('pvc.yaml', 'PVCs: models-pvc (100Gi), postgres-pvc (10Gi)'),
    ('crds.yaml', '4 CRDs customizadas (LLMInferenceStack, LLMModelRuntime, LLMProvider, LLMTenant)'),
    ('extras.yaml', 'Ingress, ServiceAccount, Role, RoleBinding, NetworkPolicy'),
]
add_table(['Arquivo', 'Conteúdo'], k8s_resources)

doc.add_heading('Helm Chart', level=2)
helm_info = [
    ('Nome', 'llm-inference-stack'),
    ('Versão do Chart', '0.1.0'),
    ('appVersion', '1.9.3'),
    ('Tipo', 'application'),
    ('Templates', '_helpers.tpl, deployment-control-plane.yaml, configmap.yaml, secret.yaml'),
    ('Features', 'Autoscaling (1-100), Ingress, TLS, nodeSelector, affinity, tolerations'),
]
add_table(['Campo', 'Valor'], helm_info)

doc.add_page_break()

# ============================================================
# 12. CI/CD
# ============================================================
doc.add_heading('12. CI/CD Pipelines', level=1)
doc.add_paragraph('O projeto mantém pipelines dualos: GitHub Actions e GitLab CI.')

doc.add_heading('GitHub Actions', level=2)
gh_workflows = [
    ('ci.yml', 'Lint (ruff), testes backend (pytest + PostgreSQL + Redis), build frontend, integrity checks'),
    ('security.yml', 'Secrets scanning, dependency audit (safety, npm audit), validação de .env'),
    ('docker-build.yml', 'Build de imagens Docker (control-plane, admin-ui)'),
    ('release-validation.yml', 'Stabilization check, smoke/chaos, operational readiness, SBOM, signing'),
    ('chaos.yml', 'Experimentos de chaos engineering em PRs e releases'),
    ('compliance.yml', 'Compliance readiness lint, evidence dry-run, release gate'),
    ('docs-validation.yml', 'Validação de CHANGELOG, links markdown, release notes'),
    ('k8s-validation.yml', 'Helm template validation, k8s-validate'),
    ('deploy-appliance.yml', 'Deploy appliance'),
    ('deploy-kubernetes.yml', 'Deploy Kubernetes'),
    ('deploy-pilot.yml', 'Deploy pilot'),
]
add_table(['Workflow', 'Descrição'], gh_workflows)

doc.add_heading('GitLab CI', level=2)
doc.add_paragraph('Pipeline de 9 estágios com 9 módulos:')
gl_stages = [
    ('preflight', 'Verificações pré-pipeline'),
    ('lint', 'Ruff (Python), ESLint (TypeScript)'),
    ('test', 'Pytest com PostgreSQL + Redis, npm build'),
    ('security', 'Secrets scanning, dependency audit'),
    ('build', 'Docker builds'),
    ('validate', 'Helm template, architecture boundaries'),
    ('chaos', 'Chaos engineering (safe-ci para MRs, extended para releases)'),
    ('package', 'SBOM, artifact signing'),
    ('release', 'Release gate, deploy automation'),
]
add_table(['Estágio', 'Função'], gl_stages)

doc.add_heading('Pre-commit Hook', level=2)
doc.add_paragraph('O hook .githooks/pre-commit executa scripts/check-secrets.sh --staged antes de cada commit.')

doc.add_page_break()

# ============================================================
# 13. MONITORAMENTO
# ============================================================
doc.add_heading('13. Monitoramento e Observabilidade', level=1)

doc.add_heading('Prometheus', level=2)
doc.add_paragraph('Scraping de control-plane:8080/metrics a cada 15 segundos.')

doc.add_heading('Alert Rules', level=2)
alerts = [
    ('HighErrorRate', 'Crítico', '5xx > 5% em 5 minutos'),
    ('LatencyBreachP95', 'Warning', 'p95 > 2s em 5 minutos'),
    ('GPUMemoryPressure', 'Warning', 'GPU memória > 90%'),
]
add_table(['Alerta', 'Severidade', 'Condição'], alerts)

doc.add_heading('Dashboards Grafana', level=2)
dashboards = [
    ('Platform Overview', 'SLO availability (99.9%), requests/sec por model_id'),
    ('GPU Capacity', 'Utilização de memória GPU (%), temperatura GPU'),
    ('SLO & Error Budget', 'Error budget remaining, burn rate'),
    ('Runtime Nodes', 'Contagem de nodes, uso de CPU por instância'),
]
add_table(['Dashboard', 'Métricas'], dashboards)

doc.add_heading('SLOs Definidos', level=2)
slos = [
    ('API Availability', '99.9%'),
    ('Latency p95', '< 2.0s'),
    ('Queue Wait Time p95', '< 5.0s'),
    ('Provider Fallback Rate', '< 5%'),
    ('Error Rate', '< 1%'),
    ('Cache Hit Ratio', '> 20%'),
    ('Model Activation Success', '99.9%'),
]
add_table(['SLO', 'Meta'], slos)

doc.add_page_break()

# ============================================================
# 14. SEGURANÇA
# ============================================================
doc.add_heading('14. Segurança', level=1)

doc.add_heading('Autenticação e Autorização', level=2)
auth_features = [
    ('API Keys', 'Chaves por cliente (sk-local-...), hashing PBKDF2-SHA256, prefixo para display'),
    ('Admin Tokens', 'Hierarquia: READ < WRITE < SUPER, toggle RBAC via config'),
    ('Bearer Token', 'Header Authorization: Bearer para clientes'),
    ('X-Admin-Token', 'Header para endpoints administrativos'),
    ('IP Policy', 'Enforcement de política de IP por cliente'),
]
add_table(['Feature', 'Descrição'], auth_features)

doc.add_heading('Headers de Segurança (Nginx)', level=2)
headers = [
    ('X-Content-Type-Options', 'nosniff'),
    ('X-Frame-Options', 'SAMEORIGIN'),
    ('Referrer-Policy', 'no-referrer'),
    ('Permissions-Policy', 'geolocation=(), microphone=(), camera=()'),
    ('Content-Security-Policy', "default-src 'self' 'unsafe-inline'; object-src 'none'"),
]
add_table(['Header', 'Valor'], headers)

doc.add_heading('Outras Features de Segurança', level=2)
sec_features = [
    'NetworkPolicy no Kubernetes restringindo ingress do control-plane',
    'ServiceAccount com Role read-only para pods/services/configmaps/secrets',
    'Detecção de abuso com auto-suspensão de clientes',
    'Monitoramento de segurança (repeated errors, large prompts, plan abuse)',
    'Pre-commit hook para scanning de secrets',
    'CORS deny-by-default',
    'Chaves de API com rotação suportada',
    'PKI e hardware trust (desabilitado por padrão)',
]
for f in sec_features:
    doc.add_paragraph(f, style='List Bullet')

doc.add_page_break()

# ============================================================
# 15. COMPLIANCE
# ============================================================
doc.add_heading('15. Compliance (SOC 2 / ISO 27001)', level=1)
doc.add_paragraph('Framework integrado de preparação para SOC 2 Type 1/2 e ISO 27001:2022.')

doc.add_heading('Controles Mapeados', level=2)
controls = [
    ('SOC2-CC6.1', 'RBAC Enforcement', 'Implementado', 'Acesso admin restrito por roles'),
    ('ISO-A.9.1.1', 'Access Control Policy', 'Implementado', 'Política de acesso definida'),
    ('SOC2-CC8.1', 'Automated Release Gates', 'Implementado', 'Gates de qualidade/security antes de deploy'),
    ('ISO-A.12.1.2', 'Change Management', 'Implementado', 'Processo formal de tracking de mudanças'),
    ('SOC2-CC7.1', 'Audit Logging', 'Implementado*', 'Logs coletados (* alerting unificado não totalmente automatizado)'),
    ('SOC2-CC7.3', 'Incident Response', 'Implementado', 'Timeline e resposta padronizada'),
    ('ISO-A.15.1.1', 'Supplier Security', 'Implementado', 'SBOM + signing para supply chain'),
    ('ISO-A.17.1.1', 'Business Continuity', 'Implementado', 'Chaos engineering para resiliência'),
]
add_table(['Control ID', 'Título', 'Status', 'Descrição'], controls)

doc.add_heading('Políticas', level=2)
policies = [
    ('Política de Segurança da Informação', 'CISO', 'Anual', 'Draft'),
    ('Política de Controle de Acesso', 'Security Admin', 'Trimestral', 'Draft'),
    ('Política de Desenvolvimento Seguro', 'Lead Architect', 'Anual', 'Draft'),
]
add_table(['Política', 'Owner', 'Review', 'Status'], policies)

doc.add_heading('Risk Register', level=2)
risks = [
    ('R001', 'Acesso não autorizado ao Admin API', '5', '2', '10', 'RBAC + MFA + Audit Logging'),
    ('R002', 'Vazamento de secrets em CI logs', '4', '3', '12', 'Secret scanning automatizado em PRs'),
]
add_table(['ID', 'Risco', 'Impacto', 'Probabilidade', 'Score', 'Mitigação'], risks)

doc.add_page_break()

# ============================================================
# 16. CHAOS ENGINEERING
# ============================================================
doc.add_heading('16. Chaos Engineering', level=1)
doc.add_paragraph(
    'Framework de chaos engineering com cenários JSON, integração CI/CD e controle de blast radius.'
)

doc.add_heading('Cenários', level=2)
chaos_scenarios = [
    ('safe-ci/', 'Cenários seguros para CI (ex: provider_timeout.json)'),
    ('extended/', 'Cenários estendidos para validação de release'),
    ('manual/', 'Cenários para execução manual'),
]
add_table(['Diretório', 'Uso'], chaos_scenarios)

doc.add_heading('Exemplo de Cenário: provider_timeout.json', level=2)
scenario_details = [
    ('Tipo', 'Injeção de timeout de provider'),
    ('Ratio', '50%'),
    ('Timeout', '5 segundos'),
    ('Janela', '30 segundos'),
    ('Assertion', 'Fallback com HTTP 200'),
    ('Rollback', 'Reset de timeouts'),
    ('Blast Radius', 'Baixo'),
]
add_table(['Parâmetro', 'Valor'], scenario_details)

doc.add_heading('Variáveis de Ambiente', level=2)
chaos_env = [
    ('CHAOS_ENABLED', 'false', 'Habilita chaos engineering'),
    ('CHAOS_ENVIRONMENT', '', 'Ambiente alvo'),
    ('CHAOS_ALLOW_PRODUCTION', 'false', 'Bloqueia injeção em produção'),
]
add_table(['Variável', 'Default', 'Descrição'], chaos_env)

doc.add_page_break()

# ============================================================
# 17. GOVERNANÇA
# ============================================================
doc.add_heading('17. Governança e Políticas', level=1)

doc.add_heading('ADRs (Architecture Decision Records)', level=2)
adrs = [
    ('0001', 'Deterministic Runtime', 'Aceito', 'Runtime deve priorizar inputs canônicos e artefatos reproduzíveis'),
    ('0002', 'Offline-First Sovereign Mode', 'Aceito', 'Modo soberano deve ser offline-first'),
    ('0003', 'Cryptographic Receipts', 'Aceito', 'Receipts com hash imutável e metadados de assinatura'),
    ('0004', 'Governance Policy Gates', 'Aceito', 'Policy gates como pontos de avaliação declarados'),
    ('0005', 'No Mandatory SaaS', 'Aceito', 'Nenhum componente central requer SaaS obrigatório'),
    ('0006', 'Placeholder Attestation Policy', 'Aceito', 'Attestation tratada como placeholder, não claims reais'),
]
add_table(['ADR', 'Título', 'Status', 'Decisão'], adrs)

doc.add_heading('RFCs', level=2)
rfcs = [
    ('0000', 'RFC Process', 'Aceito', 'Define ciclo de vida do RFC'),
    ('0001', 'Extension Runtime Governance', 'Draft', 'Restrições de governança para runtime de extensões'),
    ('0002', 'Sovereign Federation Governance', 'Draft', 'Expectativas de governança para federação soberana'),
]
add_table(['RFC', 'Título', 'Status', 'Resumo'], rfcs)

doc.add_heading('Policy-as-Code', level=2)
doc.add_paragraph(
    'Framework enterprise de Policy-as-Code com Policy Registry (ciclo draft/published/active/deprecated), '
    'Policy Engine (avaliação de regras, simulação, detecção de drift), JSON rule bundles para routing, '
    'billing e QoS, modos Disabled/Dry Run/Enforce, e detecção de drift (config_drift, runtime_override, '
    'missing_rule, stale_bundle).'
)

doc.add_heading('Governance Supervisor AI', level=2)
doc.add_paragraph(
    'Supervisor autônomo de governança (Phase 60) com Risk Engine (scoring multidimensional), '
    'Auto-Remediation (throttling, quarantining, pausing), modos Advisory/Dry Run/Guarded Enforce/Sovereign Restricted, '
    'e explicabilidade para cada decisão. Explicitamente não é AGI — é um sistema de orquestração baseado em regras.'
)

doc.add_page_break()

# ============================================================
# 18. TESTES
# ============================================================
doc.add_heading('18. Testes', level=1)
doc.add_paragraph(
    'Suite de testes extensa com 737 arquivos de teste usando pytest + pytest-asyncio.'
)

doc.add_heading('Estrutura de Testes', level=2)
test_dirs = [
    ('architecture/', '6', 'Boundaries de domínio, dependency graph, naming'),
    ('build/', '2', 'Integridade Alembic, Makefile governance'),
    ('compliance/', '1', 'Validação de claims policy'),
    ('contracts/', '6', 'Contratos de attestation, model runtime, plugins, providers, routing'),
    ('docs/', '3', 'Validação de ADR, governance docs, platform docs'),
    ('domains/', '1', 'Validação de domain contracts'),
    ('e2e/', '15+', 'Fluxos end-to-end: RBAC, billing, API keys, hot-swap, RAG, routing'),
    ('governance/', '10+', 'Policy DSL, conflitos, data governance, human governance'),
    ('kubernetes/', '3+', 'Operator mock, validação YAML'),
    ('operations/', '120+', 'Fases 69-82: adapters, attestation, federation, plugins, remediation'),
    ('performance/', '5+', 'Baseline de performance'),
    ('releases/', '3+', 'Release engineering, v1 readiness'),
    ('runtime/', '5+', 'Distributed runtime, GPU orchestrator'),
    ('security/', '5+', 'Security review interna'),
    ('services/', '20+', 'Invariants, billing, routing, quota, rate limiting'),
    ('Root test_*.py', '50+', 'Billing, abuse, admin, cache, CORS, embeddings, providers, RAG, routing, wallet'),
]
add_table(['Diretório', 'Arquivos', 'Cobertura'], test_dirs)

doc.add_heading('Conftest.py', level=2)
doc.add_paragraph(
    'Fixtures compartilhadas incluem FakeRedis (Redis in-memory async), isolated_db_url (SQLite temporário), '
    'fastapi_app/async_client para testes HTTP, admin_client com dependency overrides, '
    'e global_reset autouse fixture para limpar cache de settings entre testes.'
)

doc.add_page_break()

# ============================================================
# 19. DOCUMENTAÇÃO
# ============================================================
doc.add_heading('19. Documentação', level=1)
doc.add_paragraph('O projeto mantém 140+ arquivos de documentação em docs/.')

doc_categories = [
    ('architecture/', '25', 'Platform overview, domain map, bounded contexts, invariants, glossary, phase timeline'),
    ('releases/', '19', 'Release notes v1.9.3-v1.9.7, stabilization, release process, SBOM, versioning'),
    ('enterprise/', '8', 'Onboarding guide, pilot runbook, production handover, security questionnaire, support model'),
    ('governance/', '14', 'ADRs, RFCs, policy DSL, semantic version, supply chain, threat modeling, Makefile governance'),
    ('security/', '9', 'Admin RBAC, attestation, hardware trust, PKI, supply chain, threat model'),
    ('compliance/', '7', 'Claims policy, control mapping, ISMS readiness, SOC 2 readiness, ISO 27001 readiness'),
    ('operations/', '38', 'Platform runbook, SLOs, phase summaries 69-82, adapters, federation, plugins, remediation'),
    ('integrations/', '4', 'AnythingLLM, LangChain, n8n, Open WebUI'),
    ('Root docs/', '100+', 'Billing, RAG, TTS, routing, cache, crypto receipts, sovereign AI, workflows, etc.'),
]
add_table(['Categoria', 'Arquivos', 'Conteúdo'], doc_categories)

doc.add_page_break()

# ============================================================
# 20. SCRIPTS
# ============================================================
doc.add_heading('20. Scripts Operacionais', level=1)
doc.add_paragraph('O diretório scripts/ contém 385+ scripts shell e Python.')

script_categories = [
    ('Instalação & Setup', 'install.sh, install-local-appliance.sh, first-run-local.sh, configure-local-wizard.sh, preflight-check.sh'),
    ('Lifecycle', 'up.sh, down.sh, backup.sh, restore-local.sh, upgrade-local.sh, rollback-local.sh, deploy-appliance.sh, deploy-kubernetes.sh'),
    ('Validação (50+)', 'validate-architecture-boundaries.py, validate-runtime-contracts.py, validate-phase_69-82.py, validate-customer-ready.sh, validate-post-install-local.sh'),
    ('Comercial/Enterprise (30+)', 'validate-commercial-guardrails.sh, validate-commercial-federation.sh, validate-commercial-ha.sh, validate-commercial-global-router.sh'),
    ('Segurança', 'check-secrets.sh, security-report-local.sh, validate-cryptographic-receipts.sh, validate-model-supply-chain.sh'),
    ('Demo/Sales', 'customer-demo-local.sh, seed-commercial-demo-pack.sh, generate-client-proposal.sh, generate-sow-local.sh'),
    ('Benchmarking', 'benchmark-model-local.sh, benchmark.sh, benchmark-runtime.sh'),
    ('Chaos Engineering', 'chaos-run.sh, chaos-ci-runner.sh, chaos-list.sh, chaos-report.sh'),
    ('Shared Libraries', 'common.sh, project-root.sh, validation-logging.sh, redaction.sh, operator-errors.sh'),
    ('Compliance', 'compliance-check.sh, collect-compliance-evidence.sh, compliance-release-gate.sh, generate-compliance-pack.sh'),
]
add_table(['Categoria', 'Exemplos'], script_categories)

doc.add_page_break()

# ============================================================
# 21. CONTRATOS
# ============================================================
doc.add_heading('21. Contratos e Propostas Comerciais', level=1)

doc.add_heading('Templates de Contratos', level=2)
contracts = [
    ('SOW_TEMPLATE.md', 'Statement of Work — escopo, entregáveis, cronograma, critérios de aceite'),
    ('SERVICE_AGREEMENT_TEMPLATE.md', 'Contrato de prestação de serviços — responsabilidades, disponibilidade, propriedade dos dados'),
    ('SUPPORT_TERMS_TEMPLATE.md', 'Termos de suporte — níveis, SLA, canais, exclusões'),
    ('ACCEPTANCE_CRITERIA_TEMPLATE.md', 'Critérios formais de aceite para implantação'),
]
add_table(['Template', 'Descrição'], contracts)

doc.add_heading('Templates de Propostas', level=2)
proposals = [
    ('COMMERCIAL_PROPOSAL_TEMPLATE.md', 'Proposta comercial padrão'),
    ('TECHNICAL_PROPOSAL_TEMPLATE.md', 'Proposta técnica detalhada'),
    ('LOCAL_AI_APPLIANCE_ONE_PAGER.md', 'Visão geral em uma página'),
]
add_table(['Template', 'Descrição'], proposals)

doc.add_page_break()

# ============================================================
# 22. TOOLS
# ============================================================
doc.add_heading('22. Ferramentas (Tools)', level=1)

doc.add_heading('Public Verifier', level=2)
doc.add_paragraph(
    'CLI standalone para verificação de provas criptográficas exportadas da plataforma. '
    'Inclui verificação de caminhos Merkle, consistência de provas, cadeia de timeline, '
    'e verificação de assinaturas (placeholder Ed25519).'
)

verifier_files = [
    ('verifier_core.py', 'Lógica de verificação: Merkle path, proof consistency, timeline chain'),
    ('verifier_models.py', 'Modelos Pydantic para execution proofs, Merkle inclusion proofs'),
    ('verifier_reports.py', 'Geração de relatórios de verificação'),
    ('verifier_cli.py', 'Entry point CLI'),
]
add_table(['Arquivo', 'Função'], verifier_files)

doc.add_page_break()

# ============================================================
# 23. ESTATÍSTICAS
# ============================================================
doc.add_heading('23. Estatísticas do Código', level=1)

stats = [
    ('Arquivos Python (control_plane)', '888'),
    ('Arquivos Python (total, excluindo venv/cache)', '3.259'),
    ('Arquivos de Teste', '737'),
    ('Scripts Shell', '385'),
    ('Arquivos Frontend (TS/JS)', '42'),
    ('Arquivos de Documentação (docs/)', '140+'),
    ('API Routers', '100+'),
    ('ORM Models', '120+'),
    ('Serviços', '70+'),
    ('Makefile targets', '200+'),
    ('Variáveis de ambiente (.env.example)', '300+'),
    ('Feature flags', '200+'),
    ('Dockerfiles', '5'),
    ('Grafana Dashboards', '4'),
    ('Prometheus Alert Rules', '3'),
    ('GitHub Actions Workflows', '11'),
    ('GitLab CI Stages', '9'),
    ('ADRs', '6'),
    ('RFCs', '3'),
    ('Compliance Policies', '3'),
    ('CRDs Kubernetes', '4'),
    ('Bounded Contexts', '14'),
    ('Diretórios raiz', '46'),
    ('Releases documentados', '48'),
]
add_table(['Métrica', 'Valor'], stats)

doc.add_page_break()

# ============================================================
# 24. ROADMAP
# ============================================================
doc.add_heading('24. Roadmap e Fases', level=1)
doc.add_paragraph('O projeto completou as fases 66 a 82 do roadmap de desenvolvimento.')

phases = [
    ('Phase 66', 'Readiness Gate', 'Gate de prontidão para estabilização'),
    ('Phase 69', 'Failure Forecasting', 'Predição de falhas com sinais de anomalia'),
    ('Phase 70', 'Correlation Engine', 'Engine de correlação operacional'),
    ('Phase 71', 'Remediation Planning', 'Planejamento de remediação automatizado'),
    ('Phase 72', 'Remediation Execution', 'Execução de remediação com kill switches'),
    ('Phase 73', 'Adapter Sandbox', 'Sandbox para testes de adaptadores'),
    ('Phase 74', 'Adapter Registry', 'Registry assinado de adaptadores'),
    ('Phase 75', 'Adapter Promotion', 'Workflow de promoção de adaptadores'),
    ('Phase 76', 'Attestation Framework', 'Framework de attestation soberano'),
    ('Phase 77', 'Federation Sync', 'Protocolo de sincronização de federação'),
    ('Phase 78', 'Compatibility Contracts', 'Negociação de versão e contratos de compatibilidade'),
    ('Phase 79', 'Plugin Runtime', 'Runtime ABI de plugins'),
    ('Phase 80', 'Plugin Supply Chain', 'Proveniência e supply chain de plugins'),
    ('Phase 81', 'Reproducible Builds', 'Verificação de builds reproduzíveis'),
    ('Phase 82', 'Platform Sustainability', 'Sustentabilidade da plataforma'),
]
add_table(['Fase', 'Nome', 'Descrição'], phases)

# ============================================================
# FOOTER
# ============================================================
doc.add_page_break()
doc.add_heading('Informações do Relatório', level=1)
footer_info = [
    ('Gerado em', datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')),
    ('Ferramenta', 'OpenClaude (mimo-v2.5-pro)'),
    ('Branch', 'release/v1.8.3'),
    ('Commit HEAD', '0c25240'),
    ('Repositório', '/home/kleber/llm-inference-stack'),
]
add_table(['Campo', 'Valor'], footer_info)

doc.add_paragraph()
doc.add_paragraph('--- Fim do Relatório ---').alignment = WD_ALIGN_PARAGRAPH.CENTER

# Save
output_path = '/home/kleber/llm-inference-stack/RELATORIO_SISTEMA_LLM_INFERENCE_STACK.docx'
doc.save(output_path)
print(f'Relatório salvo em: {output_path}')
