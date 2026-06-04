import datetime
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

doc = Document()

for section in doc.sections:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(11)

def add_heading(text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x1A, 0x3C, 0x6E)
    return h

def add_table(headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.autofit = True
    hdr = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(10)
    for row_data in rows:
        row = table.add_row()
        for i, val in enumerate(row_data):
            cell = row.cells[i]
            cell.text = str(val)
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(10)
    return table

add_heading('Relatório Detalhado do Sistema', level=0)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('LLM Inference Stack & Agentic AI Platform')
run.bold = True
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(0x1A, 0x3C, 0x6E)

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
run2 = p2.add_run(f'Gerado em: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}')
run2.font.size = Pt(10)
run2.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

doc.add_paragraph()

# 1. IDENTIFICAÇÃO DO PROJETO
add_heading('1. Identificação do Projeto', level=1)

try:
    with open('/home/kleber/llm-inference-stack/VERSION') as f:
        version = f.read().strip()
except:
    version = 'N/D'

add_table(
    ['Atributo', 'Valor'],
    [
        ['Nome do Projeto', 'LLM Inference Stack & Agentic AI Platform'],
        ['Versão Atual', version],
        ['Tipo', 'Plataforma de inferência de IA on-premise, soberana e offline-first'],
        ['Linguagem Principal', 'Python 3.12 (backend) / TypeScript/React 19 (frontend)'],
        ['Framework Backend', 'FastAPI 0.115.12'],
        ['Banco de Dados', 'PostgreSQL 16 + Redis 7'],
        ['Licença', 'Proprietária'],
        ['Diretório Raiz', '/home/kleber/llm-inference-stack'],
    ]
)

# 2. ESTRUTURA DE DIRETÓRIOS
add_heading('2. Estrutura de Diretórios', level=1)

tree = """/
├── .devcontainer/          # Configuração de dev container (VS Code)
├── .github/                # GitHub Actions CI/CD (14 workflows)
├── .gitlab/                # GitLab CI/CD
├── .githooks/              # Git hooks de pré-commit
├── agents/                 # Configuração/cache de agentes
├── artifacts/              # Artefatos de build, relatórios
├── bin/                    # Binários
├── chaos/                  # Experimentos de engenharia de caos
├── commercial/             # Templates, checklists, pacotes comerciais
├── config/                 # Configurações da plataforma (25+ arquivos)
├── contracts/              # Templates de contratos legais/SOW
├── control_plane/          # Backend principal (FastAPI)
│   ├── app/                # Código fonte da aplicação
│   │   ├── api/            # 187 roteadores de API
│   │   ├── core/           # Config, logging, métricas, segurança
│   │   ├── contracts/      # Contratos de dados
│   │   ├── db/             # Sessão de BD, base, Redis
│   │   ├── domains/        # 15 bounded contexts (DDD)
│   │   ├── models/         # 150 modelos SQLAlchemy
│   │   ├── schemas/        # Schemas Pydantic
│   │   ├── services/       # 96 módulos de serviço
│   │   ├── workers/        # Workers background
│   │   └── main.py         # Entry point FastAPI
│   ├── alembic/            # Migrações de banco de dados
│   └── tests/              # Testes do control plane
├── data/                   # Dados em runtime (PKI, plugins, RAG)
├── data_plane_mock/        # Mock do data plane para testes
├── demo/                   # Assets de demonstração
├── demo-pack/              # Pacote comercial de demonstração
├── deploy/                 # Configurações de deploy
│   ├── automation/         # Scripts de automação
│   ├── helm/               # Helm charts para Kubernetes
│   └── kubernetes/         # Manifestos Kubernetes
├── docker/                 # Dockerfiles (7 serviços)
├── docs/                   # 203 documentos de documentação
├── examples/               # Exemplos de uso (8 categorias)
├── exports/                # Exportações de dados
├── frontend/               # Frontends React 19
│   ├── admin/              # Dashboard Administrativo
│   └── client/             # Portal do Cliente
├── logs/                   # Logs do sistema
├── models/                 # Arquivos GGUF (gitignored)
├── monitoring/             # Stack de observabilidade
│   ├── grafana/            # Dashboards Grafana
│   ├── prometheus/         # Config Prometheus
│   ├── otel/               # OpenTelemetry Collector
│   ├── loki/               # Loki logs
│   ├── promtail/           # Promtail agent
│   └── tempo/              # Tempo tracing
├── proposals/              # Propostas geradas para clientes
├── releases/               # Pacotes de release
├── reports/                # Relatórios gerados
├── sdk/                    # SDKs para clientes
│   ├── python/             # SDK Python (kleberai)
│   ├── node/               # SDK Node.js (TypeScript)
│   └── go/                 # SDK Go
├── scripts/                # 517 scripts operacionais
│   └── llm_harness/        # Sub-pacote LLM Harness (52 arquivos)
├── tests/                  # 644+ arquivos de teste
│   ├── api/                # Testes de API
│   ├── architecture/       # Testes de arquitetura
│   ├── chaos/              # Testes de caos/resiliência
│   ├── compliance/         # Testes de compliance
│   ├── e2e/                # Testes end-to-end
│   ├── e2e-playwright/     # Testes E2E browser
│   ├── evals/              # Avaliações de agente
│   ├── load/               # Testes de carga
│   ├── security/           # Testes de segurança
│   └── ... (outras categorias)
└── tools/                  # Ferramentas de verificação"""

p = doc.add_paragraph(tree, style='No Spacing')
for run in p.runs:
    run.font.size = Pt(8)
    run.font.name = 'Consolas'

doc.add_page_break()

# 3. BACKEND
add_heading('3. Backend - Control Plane', level=1)

doc.add_paragraph(
    'O backend é construído com FastAPI 0.115.12 em Python 3.12, seguindo os princípios de '
    'Domain-Driven Design (DDD) com 15 bounded contexts. A arquitetura é organizada em camadas: '
    'API, Service, Model, Domain e Core.'
)

add_heading('3.1. Camada de API', level=2)
doc.add_paragraph(
    '187 roteadores de API organizados por domínio, incluindo: endpoints compatíveis com OpenAI '
    '(/v1/chat/completions, /v1/models), CRUD administrativo para clientes, modelos, provedores, '
    'faturamento e RBAC; APIs da plataforma de agentes (agentes, ferramentas, memória, avaliações, '
    'marketplace, studio); recursos comerciais (roteamento global, QoS, federação, guardrails, '
    'atestação); operações (correlação, remediação, sandbox de adaptadores).'
)

add_heading('3.2. Camada de Serviços', level=2)
doc.add_paragraph(
    '96 módulos de serviço implementando a lógica de negócios, incluindo: execução de agentes, '
    'memória, ferramentas, planejamento, protocolo MCP, avaliações; faturamento (geração de '
    'notas fiscais, engine de preços, recargas de wallet); roteamento inteligente com fallback '
    'e QoS; adaptadores multi-provedor (OpenAI, Anthropic, DeepSeek); processamento de documentos '
    'RAG; engine de políticas, compliance e atestação; remediação e correlação de eventos.'
)

add_heading('3.3. Camada de Modelos', level=2)
doc.add_paragraph(
    '150 modelos SQLAlchemy ORM cobrindo: núcleo (cliente, api_key, plano de faturamento, '
    'generation_job, inference_backend); agentes (modelos de Agent, sessões, ferramentas, '
    'memória, deployments); comercial (tiers de QoS, federação, compliance, configurações de '
    'roteamento); segurança (eventos de abuso, PKI, atestação).'
)

add_heading('3.4. Bounded Contexts (DDD)', level=2)
domains = [
    ('core_runtime', 'Abstrações determinísticas de runtime'),
    ('governance', 'Engine de políticas, aprovações, decisões de compliance'),
    ('federation', 'Contratos de federação offline-first e sincronização'),
    ('plugin_runtime', 'Carregamento hardening de plugins, sandbox ABI'),
    ('supply_chain', 'Proveniência, linhagem de artefatos, reprodutibilidade'),
    ('operations', 'Workflows determinísticos, eventos, recuperação'),
    ('security', 'Boundaries de confiança, prontidão criptográfica, isolamento'),
    ('financial', 'Faturamento, governança financeira'),
    ('sovereign', 'Airgap, localidade, soberania do tenant'),
    ('observability', 'Métricas locais, traces, visibilidade sanitizada'),
    ('data_governance', 'Zoneamento de dados, linhagem, retenção'),
    ('disaster_recovery', 'Manifestos de backup, verificação de replay'),
    ('trust', 'Grafo de confiança, rede de testemunhas'),
    ('runtime', 'Perfis de runtime, monitoramento de integridade'),
    ('collaboration', 'Workspaces compartilhados, chat'),
]
add_table(['Domínio', 'Descrição'], domains)

doc.add_page_break()

# 4. FRONTEND
add_heading('4. Frontend', level=1)

add_heading('4.1. Dashboard Administrativo', level=2)
doc.add_paragraph(
    'React 19 + TypeScript 6, Vite 8 como build tool, MUI 5 (Material UI) como biblioteca de '
    'componentes, Tailwind CSS v4 para estilização, TanStack React Query e React Table para '
    'gerenciamento de dados, Recharts para visualização de dados, Zustand para gerenciamento de '
    'estado, Storybook para desenvolvimento de componentes, Lucide para ícones.'
)

add_heading('4.2. Portal do Cliente', level=2)
doc.add_paragraph(
    'React 19 + TypeScript 6, Vite 8 como build tool, Tailwind CSS v4 para estilização, '
    'Recharts para visualização de dados. Conjunto de dependências mais leve que o admin.'
)

# 5. SDKs
add_heading('5. SDKs para Clientes', level=1)
doc.add_paragraph('Três SDKs são disponibilizados para integração com a plataforma:')
add_table(
    ['SDK', 'Linguagem', 'Descrição'],
    [
        ['Python', 'Python 3.12', 'Pacote kleberai para integração Python'],
        ['Node.js', 'TypeScript', 'SDK Node.js para integração JavaScript/TypeScript'],
        ['Go', 'Go', 'SDK Go para integração Go'],
    ]
)

# 6. LLM HARNESS
add_heading('6. LLM Harness', level=1)
doc.add_paragraph(
    'Framework de execução agentíca governada e codificação autônoma, distribuído como pacote '
    'Python llm-harness. Localizado em scripts/llm_harness/ (52 arquivos).'
)
add_table(
    ['Comando CLI', 'Descrição'],
    [
        ['health', 'Verificação de saúde do sistema'],
        ['server', 'Inicia servidor do harness'],
        ['plugins', 'Gerenciamento de plugins'],
        ['benchmark', 'Benchmarking (coding, GSM8K, SWE-bench)'],
        ['code', 'Execução de código autônoma'],
        ['code-batch', 'Execução em lote'],
        ['security', 'Verificações de segurança'],
        ['eval', 'Avaliações de agente'],
    ]
)

doc.add_paragraph(
    'Características principais: suporte multi-provedor (OpenAI-compatible, Anthropic, etc.); '
    'execução sandboxed (Docker, gVisor, Firecracker, WASM); cognitive loopback com '
    'detecção de incerteza e meta-revisor; gerenciamento de memória (semântica, federada, '
    'longo prazo); engine de políticas, aprovações e checkpoint/replay; sistema de plugins '
    'com sandbox ABI.'
)

doc.add_page_break()

# 7. TESTES
add_heading('7. Infraestrutura de Testes', level=1)
doc.add_paragraph(
    'Mais de 644 arquivos de teste organizados em 23 categorias, utilizando pytest 8.3 '
    'com pytest-asyncio. Cobertura mínima de 75% configurada no pyproject.toml.'
)
add_table(
    ['Categoria', 'Descrição'],
    [
        ['tests/api/', 'Testes de contrato de API'],
        ['tests/architecture/', 'Testes de boundary de arquitetura'],
        ['tests/build/', 'Validação do sistema de build'],
        ['tests/chaos/', 'Experimentos de caos/resiliência'],
        ['tests/compliance/', 'Testes de evidência de compliance'],
        ['tests/contracts/', 'Conformidade de contratos'],
        ['tests/docs/', 'Quality gates de documentação'],
        ['tests/domains/', 'Testes de contrato de domínio'],
        ['tests/e2e/', 'Testes de integração end-to-end'],
        ['tests/e2e-playwright/', 'Testes E2E com browser (Playwright)'],
        ['tests/evals/', 'Datasets de avaliação de agente'],
        ['tests/governance/', 'Testes de políticas de governança'],
        ['tests/kubernetes/', 'Testes de deploy Kubernetes'],
        ['tests/llm_harness/', 'Testes unitários/integração LLM Harness'],
        ['tests/load/', 'Testes de carga'],
        ['tests/performance/', 'Baseline de performance'],
        ['tests/quality/', 'Qualidade de código'],
        ['tests/releases/', 'Validação de release'],
        ['tests/runtime/', 'Testes de runtime'],
        ['tests/security/', 'Testes de segurança'],
        ['tests/services/', 'Testes de nível de serviço'],
    ]
)

# 8. OBSERVABILIDADE
add_heading('8. Stack de Observabilidade', level=1)
add_table(
    ['Ferramenta', 'Função'],
    [
        ['Prometheus', 'Coleta de métricas'],
        ['Grafana', 'Dashboards e visualização'],
        ['OpenTelemetry Collector', 'Coleta de traces e métricas'],
        ['Loki', 'Agregação de logs'],
        ['Promtail', 'Agente de coleta de logs'],
        ['Tempo', 'Tracing distribuído'],
    ]
)

# 9. CI/CD
add_heading('9. CI/CD', level=1)
doc.add_paragraph('O projeto suporta duas plataformas de CI/CD:')

add_heading('9.1. GitHub Actions', level=2)
doc.add_paragraph(
    '14 workflows configurados: ci.yml, security.yml, chaos.yml, compliance.yml, '
    'docker-build.yml, llm-harness.yml, release-validation.yml, deploy-appliance.yml, '
    'deploy-kubernetes.yml, deploy-pilot.yml, k8s-validation.yml, docs-validation.yml, '
    'storybook-docs.yml, agent-evals.yml.'
)

add_heading('9.2. GitLab CI', level=2)
doc.add_paragraph(
    'Pipeline de 12 estágios (preflight a release) com includes para backend, frontend, '
    'e2e, security, release, docker, kubernetes, chaos, deploy, compliance, llm-harness.'
)

doc.add_page_break()

# 10. CONTAINERES
add_heading('10. Containerização e Deploy', level=1)
add_table(
    ['Dockerfile', 'Base', 'Descrição'],
    [
        ['control-plane', 'python:3.12-slim', 'Backend FastAPI multi-estágio com Docker CLI'],
        ['data-plane', 'nvidia:cuda-12.6', 'llama.cpp server com suporte CUDA'],
        ['data-plane-mock', 'python:3.12-slim', 'Mock minimalista para testes'],
        ['llm-harness', 'python:3.12-slim', 'LLM Harness standalone'],
        ['pocket-tts', 'python:3.12-slim', 'Serviço de Text-to-Speech'],
        ['caddy', 'caddy:2.10', 'Reverse proxy (produção)'],
        ['reverse-proxy', 'N/D', 'Configuração adicional de proxy'],
    ]
)

doc.add_paragraph(
    'Orquestração via docker-compose.yml com 14 serviços (postgres, redis, data-plane-gemma, '
    'data-plane-ollama, data-plane-mock, control-plane, control-plane-worker, rag-worker, '
    'agent-worker, prometheus, grafana, pocket-tts, otel-collector, loki, promtail, tempo). '
    'Deploy em Kubernetes via Helm charts e manifestos.'
)

# 11. CAPACIDADES DO SISTEMA
add_heading('11. Capacidades do Sistema', level=1)
add_table(
    ['Categoria', 'Capacidades'],
    [
        ['Inferência Core', 'API compatível OpenAI (/v1/chat/completions, /v1/models), streaming SSE, '
         'roteamento multi-provedor, hot-swap de modelos GGUF, RAG (busca semântica), TTS'],
        ['Plataforma de Agentes', 'Executor/runtime de agentes, registro de ferramentas, memória '
         '(semântica, longo prazo, federada), protocolo MCP, protocolo A2A, eval gate, '
         'aprovação humana, agent studio, canary/shadow agents, cognitive loopback'],
        ['Governança', 'Engine de políticas, compliance (SOC 2, ISO 27001), framework de atestação, '
         'recibos criptográficos, provas de execução, governança de dados, trilhas de auditoria'],
        ['Operações', 'Eventos determinísticos, engine de remediação, disaster recovery, sandbox de '
         'adaptadores, promoção/registry, engine de correlação, sincronização de federação, '
         'reprodutibilidade'],
        ['Comercial', 'Faturamento (BRL), wallets pré-pagas, tiers de QoS, gerenciamento de planos, '
         'proteção de receita, previsão, eleição de líder, roteamento global, geo-routing, guardrails'],
        ['Segurança', 'PKI, RBAC, isolamento de tenant, detecção de abuso, rate limiting, '
         'circuit breaker, varredura de segredos, controles de criptografia'],
        ['Multi-Cluster', 'Runtime distribuído, federação de clusters, heartbeat de nós, '
         'mesh networking, encaminhamento cross-cluster'],
        ['MLOps', 'Ciclo de vida de modelos, registry de modelos, tracking de experimentos, '
         'fine-tuning (opcional), suíte de benchmark'],
    ]
)

# 12. VARIÁVEIS DE AMBIENTE
add_heading('12. Feature Flags e Configuração', level=1)
doc.add_paragraph(
    'Mais de 200 variáveis de ambiente controlam o comportamento da plataforma com postura '
    'safe-by-default. Principais flags da plataforma de agentes:'
)
add_table(
    ['Variável', 'Default', 'Descrição'],
    [
        ['AGENT_RUNTIME_ENABLED', 'false', 'Execução de agentes desabilitada por padrão'],
        ['AGENT_REAL_LLM_ENABLED', 'false', 'Mock LLM por padrão'],
        ['AGENT_EXECUTION_ENABLED', 'false', 'Nenhuma execução real'],
        ['AGENT_MEMORY_ENABLED', 'false', 'Memória desligada por padrão'],
        ['AGENT_HUMAN_APPROVAL_ENABLED', 'true', 'Aprovação humana ligada por padrão'],
        ['AGENT_COGNITIVE_LOOPBACK_ENABLED', 'true', 'Aprendizado de interações'],
    ]
)

# 13. CHANGELOG
add_heading('13. Histórico de Commits Recentes', level=1)
add_table(
    ['Hash', 'Mensagem'],
    [
        ['2e8e661', 'feat: enhance LLM Harness providers, pricing and reporting'],
        ['2462edf', 'feat: add LLM Harness production core framework'],
        ['dc00bdf', 'feat: atualizações para a versão 2.0.5'],
        ['5fa4937', 'chore: stop tracking frontend build stats'],
        ['558d22b', 'chore: ignore local environment scripts and build statistics'],
        ['9bd5286', 'feat(backend): make MCP routers loaded by default in core application'],
        ['42c7858', 'docs: update client presentation scripts and capability matrix'],
        ['fdb699a', 'build: compile assets for admin-v2 and update static views'],
        ['8195086', 'feat(frontend): implement new pages for rbac, compliance, and telemetry'],
        ['e4e8c0a', 'feat(backend): implement core services and api endpoints for agent stack'],
        ['0c678f3', 'feat(db): add alembic migrations for collab chat and agent deployments'],
    ]
)

doc.add_page_break()

# 14. ARQUIVOS DE CONFIGURAÇÃO
add_heading('14. Arquivos de Configuração Raiz', level=1)
add_table(
    ['Arquivo', 'Propósito'],
    [
        ['pyproject.toml', 'Metadados do pacote llm-harness, dependências, configs de ferramentas'],
        ['Makefile', 'Interface central do operador com 200+ targets'],
        ['docker-compose.yml', 'Definição de 14 serviços conteinerizados'],
        ['docker-compose.prod.yml', 'Overlay de produção com Caddy e TLS'],
        ['ruff.toml', 'Configuração do linter Ruff (line-length 100)'],
        ['pytest.ini', 'Config global de testes (asyncio mode, markers)'],
        ['.env.example', 'Template de ambiente com 637 linhas de configuração'],
        ['.pre-commit-config.yaml', 'Hooks de pré-commit (ruff, mypy, etc.)'],
        ['CHANGELOG.md', '792 linhas de changelog multi-release'],
        ['.gitignore', 'Ignores para Python, Node, modelos, logs, etc.'],
    ]
)

# 15. RESUMO ESTATÍSTICO
add_heading('15. Resumo Estatístico', level=1)
add_table(
    ['Métrica', 'Valor Aproximado'],
    [
        ['Arquivos de código Python (backend)', '50.000+ linhas'],
        ['Arquivos TypeScript/React (frontend)', '10.000+ linhas'],
        ['Scripts shell operacionais', '517 scripts'],
        ['Arquivos de teste', '644+'],
        ['Roteadores de API', '187'],
        ['Modelos SQLAlchemy', '150'],
        ['Módulos de serviço', '96'],
        ['Bounded contexts (DDD)', '15'],
        ['Documentos de documentação', '203'],
        ['Workflows GitHub Actions', '14'],
        ['Estágios GitLab CI', '12'],
        ['Serviços Docker Compose', '14'],
        ['Dockerfiles', '7'],
        ['SDKs', '3 (Python, Node.js, Go)'],
        ['Variáveis de ambiente configuráveis', '200+'],
    ]
)

# FOOTER
doc.add_paragraph()
p_footer = doc.add_paragraph()
p_footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
run_footer = p_footer.add_run('--- Fim do Relatório ---')
run_footer.italic = True
run_footer.font.size = Pt(10)
run_footer.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

output_path = '/home/kleber/llm-inference-stack/reports/relatorio_sistema.docx'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
doc.save(output_path)
print(f'Relatório salvo em: {output_path}')
