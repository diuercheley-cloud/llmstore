#!/usr/bin/env python3
"""Generate comprehensive system report in .docx format."""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
import datetime

doc = Document()

# -- Page setup --
for section in doc.sections:
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

# -- Styles --
style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(11)

# Helper functions
def add_heading_styled(text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x1a, 0x3c, 0x6e)
    return h

def add_table(headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    # Header
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(10)
    # Data
    for row_data in rows:
        row = table.add_row()
        for i, val in enumerate(row_data):
            row.cells[i].text = str(val)
            for p in row.cells[i].paragraphs:
                for run in p.runs:
                    run.font.size = Pt(10)
    return table

def add_bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    if bold_prefix:
        run = p.add_run(bold_prefix)
        run.bold = True
        p.add_run(text)
    else:
        p.add_run(text)
    return p

# ============================================================
# TITLE PAGE
# ============================================================
doc.add_paragraph()
doc.add_paragraph()
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run('LLM Inference Stack')
run.font.size = Pt(32)
run.bold = True
run.font.color.rgb = RGBColor(0x1a, 0x3c, 0x6e)

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run('Relatório Completo do Sistema')
run.font.size = Pt(18)
run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

doc.add_paragraph()

meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = meta.add_run(f'Versão: v1.8.3\nData: {datetime.date.today().strftime("%d/%m/%Y")}\nBranch: release/v1.8.3')
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0x77, 0x77, 0x77)

doc.add_page_break()

# ============================================================
# TABLE OF CONTENTS (placeholder)
# ============================================================
add_heading_styled('Sumário', 1)
toc_items = [
    '1. Visão Geral do Projeto',
    '2. Arquitetura do Sistema',
    '3. Serviços e Infraestrutura',
    '4. Stack Tecnológica',
    '5. Funcionalidades Detalhadas',
    '6. Configuração e Variáveis de Ambiente',
    '7. Testes e Validação',
    '8. Deployment e Operações',
    '9. Documentação',
    '10. SDK e Integrações',
    '11. Segurança',
    '12. Governança e Compliance',
    '13. Billing e Financeiro',
    '14. Roadmap e Releases',
    '15. Estatísticas do Código',
]
for item in toc_items:
    p = doc.add_paragraph(item)
    p.paragraph_format.space_after = Pt(2)

doc.add_page_break()

# ============================================================
# 1. VISÃO GERAL
# ============================================================
add_heading_styled('1. Visão Geral do Projeto', 1)

add_heading_styled('1.1 Nome e Identidade', 2)
doc.add_paragraph('Nome do Projeto: LLM Inference Stack (comercializado como "Kleber AI" / "Local AI Appliance")')
doc.add_paragraph('Versão Atual: v1.8.3 (branch release/v1.8.3)')
doc.add_paragraph('Versão na base: v1.8.1-real-provider-validation (arquivo VERSION)')

add_heading_styled('1.2 O Que É', 2)
doc.add_paragraph(
    'O LLM Inference Stack é uma plataforma de inferência AI soberana, offline-first e determinística. '
    'É uma infraestrutura completa de AI on-premise que fornece uma API compatível com OpenAI, '
    'gerenciamento multi-tenant, billing, RAG (retrieval-augmented generation), TTS (text-to-speech) '
    'e extensivos controles de governança e compliance. Foi projetado para rodar inteiramente em '
    'hardware local (Linux ou WSL2) sem dependências de cloud, embora provedores cloud (OpenAI, '
    'DeepSeek, Anthropic, OpenRouter) possam ser opcionalmente habilitados.'
)

add_heading_styled('1.3 Público-Alvo', 2)
add_bullet('Empresas que necessitam soberania de dados (sem chamadas a APIs externas)', 'Soberania: ')
add_bullet('Integradores fazendo deploy de soluções AI on-premise', 'Integradores: ')
add_bullet('Operadores gerenciando múltiplos tenants com quotas, rate limiting e billing', 'Operadores: ')
add_bullet('Equipes de vendas necessitando demonstrações offline do produto', 'Vendas: ')

add_heading_styled('1.4 Princípios de Design', 2)
principles = [
    ('Determinístico: ', 'Resultados reproduzíveis e auditáveis'),
    ('Replay-safe: ', 'Eventos podem ser re-executados com segurança'),
    ('Offline-first: ', 'Funciona sem conectividade externa'),
    ('Soberano: ', 'Dados nunca saem do ambiente do cliente'),
    ('Advisory-first: ', 'Validação e políticas rodam em modo dry-run por padrão'),
]
for bold, text in principles:
    add_bullet(text, bold)

doc.add_page_break()

# ============================================================
# 2. ARQUITETURA
# ============================================================
add_heading_styled('2. Arquitetura do Sistema', 1)

add_heading_styled('2.1 Contextos Delimitados (Bounded Contexts)', 2)
doc.add_paragraph(
    'A plataforma é organizada em 12 contextos delimitados com contratos explícitos:'
)
contexts = [
    ('core_runtime', 'Abstrações determinísticas do runtime'),
    ('governance', 'Motor de políticas, aprovações, compliance'),
    ('federation', 'Contratos de federação offline-first e sincronização'),
    ('plugin_runtime', 'Carregamento de plugins, sandbox ABI'),
    ('supply_chain', 'Proveniência, linhagem de artefatos'),
    ('operations', 'Workflows determinísticos, eventos, recuperação'),
    ('security', 'Limites de confiança, prontidão criptográfica'),
    ('financial', 'Billing, governança financeira'),
    ('sovereign', 'Airgap, localidade, soberania de tenant'),
    ('observability', 'Métricas locais, traces'),
    ('data_governance', 'Zonamento de dados, linhagem, retenção'),
    ('disaster_recovery', 'Manifestos de backup, verificação de replay'),
]
add_table(['Contexto', 'Função'], contexts)

add_heading_styled('2.2 Estrutura de Diretórios', 2)
dirs = [
    ('control_plane/', '~200+ arquivos Python', 'Aplicação principal: FastAPI, rotas, modelos, serviços, domínios, workers, migrações Alembic'),
    ('data_plane_mock/', '1 arquivo Python', 'Mock do data plane (FastAPI) para testes sem GPU'),
    ('sdk/', 'Python + Node.js', 'Bibliotecas cliente para interação com a API'),
    ('models/', 'Arquivos GGUF', 'Armazenamento local de modelos AI (ex: gemma-4-E4B-it-Q4_0.gguf)'),
    ('monitoring/', '3 configs', 'Provisionamento Prometheus e Grafana'),
    ('docker/', '10 arquivos', 'Dockerfiles para control-plane, data-plane, data-plane-mock, pocket-tts, reverse-proxy, caddy'),
    ('config/', '7 JSONs', 'Configurações de exemplo para roteamento, pricing, branding, retenção'),
    ('contracts/', '5 Markdowns', 'Templates de contratos comerciais (SOW, acordo de serviço, termos de suporte)'),
    ('scripts/', '435 arquivos', 'Scripts de validação, operação, instalação, demo'),
    ('tests/', '685 arquivos Python', 'Suite de testes abrangente em 18 subdiretórios'),
    ('docs/', '295 arquivos', 'Documentação extensiva em 17 subdiretórios'),
    ('examples/', '24 arquivos', 'Exemplos de integração em Python, Node.js, curl, LangChain, Open WebUI, n8n, AnythingLLM'),
    ('demo/', '3 arquivos', 'Documentos RAG de demonstração'),
    ('demo-pack/', '~20 arquivos', 'Cenários de demo comerciais, dados fictícios, handling de objeções'),
    ('bin/', '7 arquivos', 'Binário llama-server pré-compilado e bibliotecas CUDA/CPU'),
    ('tools/', '~20 arquivos', 'CLI verificador público (Phase 43)'),
    ('proposals/', '5 arquivos', 'Templates de propostas comerciais e técnicas'),
    ('releases/', '19 diretórios', 'Artefatos de release de v1.4.3 a v1.8.1'),
    ('reports/', '2 arquivos', 'Relatório pronto para cliente (JSON + MD)'),
    ('artifacts/', '62 subdiretórios', 'Artefatos de validação gerados, backups, bundles de release'),
]
add_table(['Diretório', 'Arquivos', 'Propósito'], dirs)

doc.add_page_break()

# ============================================================
# 3. SERVIÇOS
# ============================================================
add_heading_styled('3. Serviços e Infraestrutura', 1)

add_heading_styled('3.1 Serviços Docker Compose', 2)
services = [
    ('postgres', 'postgres:16-alpine', '5432 (interno)', 'Banco de dados primário'),
    ('redis', 'redis:7-alpine', '6379', 'Fila e cache'),
    ('data-plane-gemma', 'Custom (llama.cpp + CUDA)', '8081', 'Backend de inferência GPU'),
    ('data-plane-ollama', 'ollama/ollama:0.9.5', '11434', 'Backend alternativo Ollama (profile: ollama)'),
    ('data-plane-mock', 'Custom Python', '8081', 'Mock de inferência para testes (profile: fallback-test)'),
    ('control-plane', 'Custom Python', '8080 (host: 18080)', 'Servidor API principal'),
    ('control-plane-worker', 'Same as control-plane', 'N/A', 'Worker de geração em background'),
    ('rag-worker', 'Same as control-plane', 'N/A', 'Worker de processamento RAG'),
    ('prometheus', 'prom/prometheus:v2.53.4', '9090', 'Métricas (profile: observability)'),
    ('grafana', 'grafana/grafana:11.1.4', '3001', 'Dashboards (profile: observability)'),
    ('pocket-tts', 'Custom', '8000', 'Serviço de text-to-speech'),
]
add_table(['Serviço', 'Imagem', 'Porta', 'Propósito'], services)

add_heading_styled('3.2 Produção (docker-compose.prod.yml)', 2)
doc.add_paragraph('O overlay de produção adiciona:')
add_bullet('Proxy reverso Caddy nas portas 80/443 com TLS automático via Let\'s Encrypt')
add_bullet('Remove exposição direta de portas para postgres, redis e control-plane')
add_bullet('Logging JSON com limites de tamanho')

add_heading_styled('3.3 Endpoints da API (Compatível com OpenAI)', 2)
endpoints = [
    ('GET', '/v1/models', 'Listar modelos disponíveis'),
    ('POST', '/v1/chat/completions', 'Chat completion (streaming SSE ou non-streaming)'),
    ('POST', '/v1/embeddings', 'Gerar embeddings'),
    ('POST', '/v1/responses', 'API de respostas (beta)'),
    ('GET', '/client/usage', 'Consulta de uso do cliente'),
    ('POST', '/client/rag/upload', 'Upload de documentos RAG'),
    ('GET', '/client/rag/search', 'Busca semântica'),
    ('POST', '/pocket-tts/tts', 'Text-to-speech'),
    ('GET', '/health', 'Health check'),
    ('GET', '/ready', 'Readiness check'),
    ('GET', '/metrics', 'Métricas Prometheus'),
]
add_table(['Método', 'Endpoint', 'Descrição'], endpoints)

add_heading_styled('3.4 Interfaces Web', 2)
uis = [
    ('/', 'Landing page'),
    ('/admin-dashboard', 'Dashboard administrativo (requer ADMIN_TOKEN)'),
    ('/admin-lab', 'Lab de gerenciamento de modelos'),
    ('/client-portal', 'Portal de self-service do cliente'),
    ('/pricing', 'Página de preços'),
    ('/capabilities', 'Página pública de capacidades'),
]
add_table(['Caminho', 'Descrição'], uis)

doc.add_page_break()

# ============================================================
# 4. STACK TECNOLÓGICA
# ============================================================
add_heading_styled('4. Stack Tecnológica', 1)

add_heading_styled('4.1 Linguagens', 2)
add_bullet('Linguagem primária para control plane, SDK, scripts, tests, tools', 'Python 3.12: ')
add_bullet('SDK Node.js, arquivos estáticos frontend', 'TypeScript/JavaScript: ')
add_bullet('400+ scripts operacionais/de validação', 'Shell (Bash): ')
add_bullet('Migrações Alembic para PostgreSQL', 'SQL: ')

add_heading_styled('4.2 Frameworks e Bibliotecas', 2)
libs = [
    ('FastAPI', '0.115.12', 'Framework web'),
    ('Uvicorn', '0.34.2', 'Servidor ASGI'),
    ('SQLAlchemy', '2.0.40 (async)', 'ORM'),
    ('Alembic', '1.15.2', 'Migrações de banco (103 arquivos)'),
    ('Pydantic', '2.11.3', 'Validação de dados'),
    ('httpx', '0.28.1', 'Cliente HTTP'),
    ('redis', '5.2.1', 'Cliente Redis'),
    ('asyncpg', '0.30.0', 'Driver PostgreSQL async'),
    ('prometheus-client', '0.21.1', 'Métricas'),
    ('sentence-transformers', '3.3.1', 'Embeddings'),
    ('pgvector', '0.3.6', 'Busca por similaridade vetorial'),
    ('pymupdf', '1.25.1', 'Parsing PDF para RAG'),
    ('langchain-text-splitters', '0.3.5', 'Chunking de texto para RAG'),
    ('PyJWT', '2.8.0', 'Autenticação JWT'),
    ('cryptography', '44.0.2', 'Operações criptográficas'),
]
add_table(['Biblioteca', 'Versão', 'Função'], libs)

add_heading_styled('4.3 Bancos de Dados', 2)
add_bullet('Banco primário com extensão pgvector', 'PostgreSQL 16 (Alpine): ')
add_bullet('Gerenciamento de filas e cache', 'Redis 7 (Alpine): ')

add_heading_styled('4.4 Backends de Inferência', 2)
add_bullet('Inferência local GPU via llama-server (compilado com CUDA 12.6)', 'llama.cpp: ')
add_bullet('Backend de inferência local alternativo', 'Ollama 0.9.5: ')
add_bullet('Backend FastAPI para testes', 'Mock backend: ')

add_heading_styled('4.5 Infraestrutura', 2)
infra = [
    ('Docker / Docker Compose', 'Containerização'),
    ('Caddy 2.10', 'Proxy reverso com TLS automático (produção)'),
    ('Nginx', 'Configuração alternativa de proxy reverso'),
    ('Prometheus / Grafana', 'Stack de observabilidade'),
    ('NVIDIA CUDA 12.6.3', 'Aceleração GPU'),
]
add_table(['Tecnologia', 'Função'], infra)

add_heading_styled('4.6 Qualidade de Código', 2)
add_bullet('Linting (regras: E, F, I; line-length: 100)', 'Ruff 0.11.8: ')
add_bullet('Testes', 'pytest 8.3.5 + pytest-asyncio 0.26.0: ')

doc.add_page_break()

# ============================================================
# 5. FUNCIONALIDADES
# ============================================================
add_heading_styled('5. Funcionalidades Detalhadas', 1)

add_heading_styled('5.1 Inferência Core', 2)
add_bullet('/v1/chat/completions compatível com OpenAI com streaming SSE')
add_bullet('/v1/embeddings com sentence-transformers locais ou mock backend')
add_bullet('/v1/responses API (beta, camada de compatibilidade simplificada)')
add_bullet('Registro multi-modelo com suporte a modelos GGUF')
add_bullet('Fila de geração assíncrona com workers em background')

add_heading_styled('5.2 Roteamento Multi-Provider (v1.8.0+)', 2)
add_bullet('Roteamento inteligente com estratégias: local_first, premium_quality, lowest_cost, coding')
add_bullet('Adaptadores para: Local (llama.cpp), LMStudio, OpenAI, Anthropic, DeepSeek, OpenRouter, Ollama')
add_bullet('Fallback cloud controlado com limites de custo')
add_bullet('Validação real de providers (opt-in, dry-run, custo limitado)')
add_bullet('Padrão circuit breaker para saúde dos providers')

add_heading_styled('5.3 RAG (Retrieval-Augmented Generation)', 2)
add_bullet('Upload de documentos (PDF, TXT, MD) com chunking')
add_bullet('Embeddings vetoriais via pgvector e sentence-transformers')
add_bullet('Busca semântica com isolamento por tenant')
add_bullet('Vault RAG empresarial com políticas e controles de segurança')

add_heading_styled('5.4 Multi-Tenancy', 2)
add_bullet('Isolamento de clientes com API keys (armazenamento hasheado)')
add_bullet('Quotas, rate limits e planos de billing por tenant')
add_bullet('Export e delete seguro de tenant')
add_bullet('Blocos de funcionalidade por cliente')

add_heading_styled('5.5 White-Label / Branding', 2)
add_bullet('Nome do produto, cores, tagline e rodapé configuráveis')
add_bullet('JSON de configuração de branding público')

add_heading_styled('5.6 Funcionalidades Comerciais', 2)
add_bullet('CRM de vendas para leads')
add_bullet('Propostas comerciais e cotações')
add_bullet('Templates de contrato/SOW')
add_bullet('Relatórios mensais de clientes')
add_bullet('Pack de demo com 5 cenários (clínica, jurídico, suporte, educação, provedor API)')
add_bullet('Dashboards executivos e exportação de relatórios')

doc.add_page_break()

# ============================================================
# 6. CONFIGURAÇÃO
# ============================================================
add_heading_styled('6. Configuração e Variáveis de Ambiente', 1)

doc.add_paragraph('O arquivo principal de configuração é .env.example (299 linhas). Principais categorias:')

add_heading_styled('6.1 Core', 2)
add_bullet('PROJECT_NAME, DEPLOYMENT_MODE (appliance|saas), APP_ENV')
add_bullet('HOST_PORT (padrão: 18080), CONTROL_PLANE_HOST/PORT')

add_heading_styled('6.2 Banco de Dados', 2)
add_bullet('POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, DATABASE_URL')
add_bullet('REDIS_URL, REDIS_PORT')

add_heading_styled('6.3 Inferência', 2)
add_bullet('MODEL_ID, MODEL_FILE, LLAMA_CTX_SIZE, LLAMA_N_GPU_LAYERS')
add_bullet('LLAMA_THREADS, LLAMA_BATCH_SIZE, LLAMA_PARALLEL')
add_bullet('MAX_CONTEXT_TOKENS, MAX_INPUT_TOKENS, DEFAULT_MAX_TOKENS')

add_heading_styled('6.4 Providers Cloud (opt-in)', 2)
add_bullet('OPENAI_PROVIDER_ENABLED, OPENAI_API_KEY, OPENAI_BASE_URL')
add_bullet('DEEPSEEK_PROVIDER_ENABLED, DEEPSEEK_API_KEY')
add_bullet('ANTHROPIC_PROVIDER_ENABLED, ANTHROPIC_API_KEY')
add_bullet('REAL_PROVIDER_VALIDATION_ENABLED, REAL_PROVIDER_MAX_COST_BRL')

add_heading_styled('6.5 Billing', 2)
add_bullet('BILLING_INVOICE_DAY, BILLING_DUE_DAYS, BILLING_SUSPEND_AFTER_DAYS')
add_bullet('MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL, MAX_CLIENT_PROVIDER_COST_PER_DAY_BRL')

add_heading_styled('6.6 RAG', 2)
add_bullet('RAG_ENABLED, RAG_STORAGE_DIR, RAG_MAX_FILE_MB')
add_bullet('RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP, RAG_TOP_K_DEFAULT')
add_bullet('RAG_EMBEDDING_PROVIDER, RAG_EMBEDDING_MODEL')

add_heading_styled('6.7 Segurança', 2)
add_bullet('ADMIN_TOKEN, CORS_ALLOW_ORIGINS, PUBLIC_SIGNUP_ENABLED')
add_bullet('ABUSE_DETECTION_ENABLED, ABUSE_AUTO_SUSPEND_ENABLED')

add_heading_styled('6.8 Governança', 2)
doc.add_paragraph(
    'Dezenas de variáveis de governança cobrindo: guardrails comerciais, promoção canary, '
    'eleição de líder HA, federação, roteamento global, traffic shifting, geo routing, '
    'QoS, planejamento de capacidade, controles de compliance, governança soberana, '
    'sincronização airgap, attestation de hardware, reprodutibilidade, timelines Merkle, '
    'e provas de execução.'
)

doc.add_page_break()

# ============================================================
# 7. TESTES
# ============================================================
add_heading_styled('7. Testes e Validação', 1)

add_heading_styled('7.1 Framework', 2)
doc.add_paragraph('Framework: pytest 8.3.5 com pytest-asyncio 0.26.0')
doc.add_paragraph('Configuração (pytest.ini): testpaths = tests, asyncio_mode = auto')

add_heading_styled('7.2 Escala dos Testes', 2)
doc.add_paragraph('685 arquivos de teste Python distribuídos em 18 subdiretórios:')

test_dirs = [
    ('tests/architecture/', 'Testes de limites arquiteturais, grafo de dependências, consistência de nomenclatura'),
    ('tests/build/', 'Governança do Makefile, validação de build'),
    ('tests/compliance/', 'Testes de controles de compliance'),
    ('tests/docs/', 'Completude da documentação e fundação de governança'),
    ('tests/domains/', 'Testes de contratos de domínio'),
    ('tests/governance/', 'DSL de políticas, governança de dados, workflows humanos, fase 82'),
    ('tests/operations/', 'Maior suite -- fases 69-82 (previsão de falhas, correlação, remediação, adaptadores, federação, plugins, builds reproduzíveis, attestation, compatibilidade)'),
    ('tests/performance/', 'Ferramentas de baseline de performance'),
    ('tests/phases/', 'Validação específica por fase'),
    ('tests/quality/', 'Warnings de framework, depreciações'),
    ('tests/releases/', 'Engenharia de release, prontidão v1'),
    ('tests/runtime/', 'Testes de contrato de runtime'),
    ('tests/security/', 'Revisão de segurança interna'),
    ('tests/services/', 'Testes de nível de serviço incluindo invariantes'),
    ('tests/validation/', 'Testes de helpers de validação'),
    ('tests/fixtures/', 'Fixtures de teste'),
]
add_table(['Diretório', 'Propósito'], test_dirs)

add_heading_styled('7.3 Hierarquia de Validação (Makefile)', 2)
validations = [
    ('validate-architecture-smoke', 'Checks estáticos rápidos (uso diário)'),
    ('validate-architecture-full', 'Suite completa incluindo testes lentos'),
    ('validate-platform', 'Architecture + governance + security'),
    ('validate-all', 'Stack completa de validação determinística'),
    ('Validadores individuais', 'Scripts e suites dedicados para fases 66-82'),
]
add_table(['Target', 'Descrição'], validations)

doc.add_page_break()

# ============================================================
# 8. DEPLOYMENT
# ============================================================
add_heading_styled('8. Deployment e Operações', 1)

add_heading_styled('8.1 Início Rápido', 2)
doc.add_paragraph('cp .env.example .env.local   # Configurar')
doc.add_paragraph('make install-local            # Instalar com dados demo')
doc.add_paragraph('make validate                 # Validar')

add_heading_styled('8.2 Targets do Makefile (1200+ linhas)', 2)
makefile_targets = [
    ('Lifecycle', 'up, down, restart, status, health'),
    ('Instalação', 'install-local, first-run, configure-local'),
    ('Validação', '80+ targets validate-* cobrindo cada aspecto'),
    ('Operações', 'backup, restore, upgrade, rollback, benchmark, smoke'),
    ('Segurança', 'security, check-secrets, readiness'),
    ('Demo', 'customer-demo, demo-pack, meeting-ready'),
    ('Vendas', 'generate-proposal, quote-demo, generate-sow'),
    ('Relatórios', 'monthly-report-demo, client-ready-report'),
]
add_table(['Categoria', 'Targets'], makefile_targets)

add_heading_styled('8.3 Backup/Restore', 2)
add_bullet('Cria backup em artifacts/backups-local/', 'make backup: ')
add_bullet('Restaura de backup', 'make restore BACKUP_DIR=/path: ')
add_bullet('Rollback para versão anterior', 'make rollback: ')
doc.add_paragraph('Backup automático antes de upgrades.')

add_heading_styled('8.4 Histórico de Releases', 2)
doc.add_paragraph('19 releases rastreados de v1.4.3 (2026-05-07) a v1.8.1 (2026-05-13), com manifests e checksums.')

doc.add_page_break()

# ============================================================
# 9. DOCUMENTAÇÃO
# ============================================================
add_heading_styled('9. Documentação', 1)
doc.add_paragraph('295 arquivos de documentação em 17 subdiretórios em docs/:')

doc_dirs = [
    ('docs/ (raiz)', '130+ docs de topo cobrindo cada feature, notas de release, guias'),
    ('docs/architecture/', 'Visão geral, mapa de domínio, garantias, modelo operacional, workflows de validação, relacionamentos, glossário, timeline de fases'),
    ('docs/adr/', 'Architectural Decision Records'),
    ('docs/compliance/', 'Documentação de compliance'),
    ('docs/demo-visual-guide/', 'Storyboard de screenshots e guia visual de demo'),
    ('docs/governance/', 'Documentação de governança'),
    ('docs/integrations/', 'Guias de integração (Open WebUI, n8n, LangChain, etc.)'),
    ('docs/operations/', 'Runbooks, comandos do operador'),
    ('docs/performance/', 'Documentação de performance'),
    ('docs/phases/', 'Documentação específica por fase'),
    ('docs/plugins/', 'Documentação de plugins'),
    ('docs/quality/', 'Documentação de qualidade'),
    ('docs/releases/', 'Documentação por release'),
    ('docs/rfc/', 'RFCs'),
    ('docs/runtime/', 'Documentação de runtime'),
    ('docs/security/', 'Documentação de segurança'),
    ('docs/validation/', 'Documentação de validação'),
]
add_table(['Subdiretório', 'Conteúdo'], doc_dirs)

doc.add_page_break()

# ============================================================
# 10. SDK
# ============================================================
add_heading_styled('10. SDK e Integrações', 1)

add_heading_styled('10.1 Python SDK (sdk/python/)', 2)
add_bullet('kleberai', 'Nome do pacote: ')
add_bullet('Client em kleberai/client.py', 'Classe principal: ')
add_bullet('chat(), models(), embeddings(), rag_query()', 'Métodos: ')
add_bullet('httpx', 'HTTP client: ')
add_bullet('http://localhost:18080', 'URL base padrão: ')

add_heading_styled('10.2 Node.js SDK (sdk/node/)', 2)
doc.add_paragraph('TypeScript compilado para JavaScript. Arquivos: dist/index.js, dist/index.d.ts.')

add_heading_styled('10.3 Cliente Python Legado', 2)
doc.add_paragraph('scripts/llm_stack_client.py -- Cliente mais abrangente (LLMStackClient) cobrindo chat, models, portal, RAG e streaming.')

add_heading_styled('10.4 Exemplos de Integração', 2)
doc.add_paragraph('24 arquivos de exemplo em examples/: Python, Node.js, curl, LangChain, Open WebUI, n8n, AnythingLLM.')

doc.add_page_break()

# ============================================================
# 11. SEGURANÇA
# ============================================================
add_heading_styled('11. Segurança', 1)

add_heading_styled('11.1 Autenticação', 2)
add_bullet('API keys com armazenamento hasheado (exibição apenas do prefixo)')
add_bullet('Token de admin para endpoints administrativos')
add_bullet('Autenticação JWT (PyJWT)')

add_heading_styled('11.2 Controles', 2)
add_bullet('Rate limiting e detecção de abuso (dry-run por padrão)')
add_bullet('CORS deny-by-default')
add_bullet('Logging de eventos de segurança')
add_bullet('Scanning de segredos no codebase')
add_bullet('Controles de criptografia por tenant')

add_heading_styled('11.3 Governança de Segurança', 2)
add_bullet('Limites de confiança (trust boundaries)')
add_bullet('Prontidão criptográfica')
add_bullet('Attestation de hardware')
add_bullet('Sandbox de adaptadores')

doc.add_page_break()

# ============================================================
# 12. GOVERNANÇA
# ============================================================
add_heading_styled('12. Governança e Compliance', 1)

doc.add_paragraph(
    'O sistema possui uma camada extensiva de governança e compliance, '
    'desenvolvida iterativamente ao longo de 82+ fases.'
)

add_heading_styled('12.1 Motor de Políticas', 2)
add_bullet('DSL de políticas customizada')
add_bullet('Controles de compliance (report-only por padrão)')
add_bullet('Governança de controles operacionais')

add_heading_styled('12.2 Operações Avançadas (Fases 69-82)', 2)
add_bullet('Sinais de falha preditiva e forecasting')
add_bullet('Motor de correlação determinístico')
add_bullet('Planejamento e execução de remediação (com aprovação)')
add_bullet('Sandbox, registro e workflows de promoção de adaptadores')
add_bullet('Contratos de compatibilidade e negociação de versão')
add_bullet('ABI de plugin e runtime de extensão')
add_bullet('Proveniência de supply chain de plugins e SBOM')
add_bullet('Verificação de build reproduzível')
add_bullet('Framework de attestation')
add_bullet('Protocolo de sincronização de federação')

add_heading_styled('12.3 Soberania', 2)
add_bullet('Governança de airgap')
add_bullet('Sincronização airgap')
add_bullet('Localidade e soberania de tenant')
add_bullet('Timelines Merkle e provas de execução')

doc.add_page_break()

# ============================================================
# 13. BILLING
# ============================================================
add_heading_styled('13. Billing e Financeiro', 1)

add_heading_styled('13.1 Rastreamento', 2)
add_bullet('Custo/preço/margem por request em Reais Brasileiros (BRL)')
add_bullet('Planos de billing com quotas (requests, tokens, embeddings, TTS)')

add_heading_styled('13.2 Faturamento', 2)
add_bullet('Geração de faturas com ciclos e suspensão')
add_bullet('Carteira prepaid com crédito/débito manual')

add_heading_styled('13.3 Proteção Financeira', 2)
add_bullet('Forecasting de receita')
add_bullet('Políticas de proteção e escalação')
add_bullet('Reconciliação financeira e gestão de disputas')
add_bullet('Limites de custo global e por cliente por dia')

doc.add_page_break()

# ============================================================
# 14. ROADMAP
# ============================================================
add_heading_styled('14. Roadmap e Releases', 1)

releases = [
    ('v1.4.3', '2026-05-07', 'Release inicial rastreado'),
    ('v1.5.x', '2026-05-07', 'Evolução de funcionalidades'),
    ('v1.6.3-v1.6.7', '2026-05-08', 'Readiness cleanup, sales ops, customer demo pack'),
    ('v1.7.0', '2026-05-09', 'Local AI Appliance'),
    ('v1.7.1', '2026-05-09', 'Post-release polish'),
    ('v1.8.0', '2026-05-12', 'Hybrid AI Platform'),
    ('v1.8.1', '2026-05-13', 'Real provider validation'),
    ('v1.8.3', '2026-05-18', 'Portal TTS, openrouter integration, admin policy controls'),
]
add_table(['Versão', 'Data', 'Destaques'], releases)

doc.add_page_break()

# ============================================================
# 15. ESTATÍSTICAS
# ============================================================
add_heading_styled('15. Estatísticas do Código', 1)

stats = [
    ('Arquivos Python source (control_plane/app)', '~200+'),
    ('Módulos de rotas API', '91'),
    ('Arquivos de modelo SQLAlchemy', '~100'),
    ('Módulos de serviço', '~70+ (21 subdiretórios)'),
    ('Módulos de domínio', '13 domínios com contratos/eventos/schemas'),
    ('Migrações Alembic', '103'),
    ('Arquivos de teste', '685'),
    ('Arquivos de documentação', '295'),
    ('Scripts Shell/Python', '435'),
    ('Targets do Makefile', '120+'),
    ('Serviços Docker Compose', '11'),
    ('Arquivos frontend estáticos', '103'),
    ('Exemplos de configuração', '7'),
    ('Exemplos de integração', '24'),
    ('Versões de release rastreadas', '19'),
]
add_table(['Métrica', 'Quantidade'], stats)

doc.add_paragraph()
doc.add_paragraph(
    'Este é uma plataforma madura, de grau empresarial, com uma camada de governança e compliance '
    'incomumente profunda. O código reflete desenvolvimento iterativo extensivo ao longo de 82+ fases, '
    'com forte ênfase em validação, segurança e prontidão operacional.'
)

# ============================================================
# SAVE
# ============================================================
output_path = '/home/kleber/llm-inference-stack/reports/relatorio_completo_sistema.docx'
doc.save(output_path)
print(f'Relatório salvo em: {output_path}')
