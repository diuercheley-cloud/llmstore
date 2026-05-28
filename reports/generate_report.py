import os
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from datetime import datetime

doc = Document()

# ── Page setup ──
for section in doc.sections:
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Cm(29.7)
    section.page_height = Cm(21.0)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

# ── Styles ──
style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(10)

for level in range(1, 5):
    hs = doc.styles[f'Heading {level}']
    hs.font.color.rgb = RGBColor(0x1B, 0x3A, 0x5C)

def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    for i, h in enumerate(headers):
        hdr.cells[i].text = h
    for row_data in rows:
        row = table.add_row()
        for i, val in enumerate(row_data):
            row.cells[i].text = str(val)
    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Cm(w)
    return table

# ════════════════════════════════════════════════════
# CAPA
# ════════════════════════════════════════════════════
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('\n\n\n\nRELATÓRIO COMPLETO DO SISTEMA')
run.bold = True
run.font.size = Pt(28)
run.font.color.rgb = RGBColor(0x1B, 0x3A, 0x5C)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('LLM Inference Stack — Análise Técnica Abrangente')
run.font.size = Pt(16)
run.font.color.rgb = RGBColor(0x4A, 0x6F, 0xA5)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run(f'Data: {datetime.now().strftime("%d/%m/%Y %H:%M")}')
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

doc.add_page_break()

# ════════════════════════════════════════════════════
# SUMÁRIO EXECUTIVO
# ════════════════════════════════════════════════════
doc.add_heading('1. Sumário Executivo', level=1)
doc.add_paragraph(
    'Este relatório documenta a análise técnica completa do repositório "LLM Inference Stack", '
    'uma plataforma soberana de IA determinística, offline-first, projetada para inferência de '
    'Modelos de Linguagem de Grande Escala (LLMs) e execução de agentes de IA em ambientes '
    'corporativos controlados. O sistema adota arquitetura de microsserviços orquestrada via '
    'Docker Compose, com opção de deployment em Kubernetes via Helm.'
)
doc.add_paragraph(
    f'• Versão atual: v2.0.2-agentic-ga-readiness\n'
    f'• Linguagem principal: Python 3.12 (backend) + TypeScript/React 19 (frontend)\n'
    f'• Commits no git: 99\n'
    f'• Arquivos de código no backend (Python): 1.107\n'
    f'• Arquivos de código no frontend (TS/TSX): 8.068\n'
    f'• Testes automatizados: 847\n'
    f'• Scripts operacionais: 491\n'
    f'• Documentos de documentação: 535\n'
    f'• Feature flags: ~3.136\n'
    f'• Rotas de API: 134\n'
    f'• Modelos SQLAlchemy: 105\n'
    f'• Módulos de serviço: 55 (gerais) + 70 (agentes) + 36 (roteamento)\n'
    f'• Contextos delimitados (DDD): 15\n'
    f'• Workflows CI/CD: 13 (GitHub Actions) + 11 estágios (GitLab CI)'
)

# ════════════════════════════════════════════════════
# ARQUITETURA DO SISTEMA
# ════════════════════════════════════════════════════
doc.add_heading('2. Arquitetura do Sistema', level=1)

doc.add_heading('2.1 Visão Geral', level=2)
doc.add_paragraph(
    'O sistema segue uma arquitetura de microsserviços com separação clara entre plano de controle '
    '(control plane) e plano de dados (data plane). O control plane gerencia requisições, '
    'autenticação, roteamento, billing, agentes e governança. O data plane executa a inferência '
    'dos modelos de linguagem propriamente ditos, utilizando llama.cpp como engine principal.'
)

doc.add_heading('2.2 Diagrama de Serviços (Docker Compose)', level=2)
add_table(doc,
    ['Serviço', 'Função', 'Imagem', 'Perfil'],
    [
        ['postgres', 'Banco de dados relacional (PostgreSQL 16)', 'postgres:16-alpine', 'Sempre'],
        ['redis', 'Cache e fila (Redis 7)', 'redis:7-alpine', 'Sempre'],
        ['data-plane-gemma', 'Inferência LLM com GPU (llama.cpp)', 'Dockerfile data-plane', 'Sempre'],
        ['data-plane-ollama', 'Inferência alternativa via Ollama', 'ollama/ollama:0.9.5', 'ollama'],
        ['data-plane-mock', 'Mock de inferência para testes', 'Dockerfile data-plane-mock', 'fallback-test'],
        ['control-plane', 'API FastAPI principal', 'Dockerfile control-plane', 'Sempre'],
        ['control-plane-worker', 'Worker de geração em background', 'Dockerfile control-plane', 'Sempre'],
        ['rag-worker', 'Worker de RAG (Retrieval-Augmented Generation)', 'Dockerfile control-plane', 'Sempre'],
        ['agent-worker', 'Worker de execução de agentes', 'Dockerfile control-plane', 'agentic'],
        ['prometheus', 'Métricas e monitoramento', 'prom/prometheus:v2.53.4', 'observability'],
        ['grafana', 'Dashboards de observabilidade', 'grafana/grafana:11.1.4', 'observability'],
        ['pocket-tts', 'Serviço de Text-to-Speech', 'Dockerfile pocket-tts', 'Sempre'],
    ],
    col_widths=[4, 7, 5, 3]
)

doc.add_heading('2.3 Fluxo de Requisição', level=2)
doc.add_paragraph(
    '1. Cliente HTTP envia requisição para o control-plane (porta 8080)\n'
    '2. FastAPI aplica middlewares (CORS, autenticação, logging, correlation ID)\n'
    '3. Roteador encaminha para o handler apropriado (134 rotas disponíveis)\n'
    '4. Para inferência: requisição é roteada ao data-plane via proxy\n'
    '5. Data-plane (llama.cpp server) processa o prompt com GPU\n'
    '6. Resposta é retornada ao cliente, possivelmente cacheada no Redis\n'
    '7. Eventos de billing, auditoria e métricas são registrados assincronamente'
)

doc.add_heading('2.4 Redes Docker', level=2)
doc.add_paragraph(
    '• control_net: Rede principal; todos os serviços conectados\n'
    '• data_net: Rede interna isolada para tráfego de dados (GPU)'
)

# ════════════════════════════════════════════════════
# BACKEND (CONTROL PLANE)
# ════════════════════════════════════════════════════
doc.add_heading('3. Backend — Control Plane (Python/FastAPI)', level=1)

doc.add_heading('3.1 Stack Tecnológica', level=2)
add_table(doc,
    ['Componente', 'Tecnologia', 'Versão'],
    [
        ['Framework Web', 'FastAPI', '—'],
        ['ORM', 'SQLAlchemy', '2.0'],
        ['Migrações', 'Alembic', '—'],
        ['Validação', 'Pydantic', 'v2'],
        ['Banco de Dados', 'PostgreSQL + SQLite (fallback)', '16'],
        ['Cache/Fila', 'Redis', '7'],
        ['Métricas', 'Prometheus (cliente)', '—'],
        ['Autenticação', 'API Key + JWT + RBAC', '—'],
        ['Executor de Tarefas', 'Workers assíncronos', '—'],
        ['Container', 'Docker (Python 3.12-slim)', '3.12'],
    ],
    col_widths=[5, 6, 3]
)

doc.add_heading('3.2 Estrutura de Diretórios', level=2)
doc.add_paragraph(
    'control_plane/\n'
    '├── alembic/          # Migrações de banco de dados\n'
    '│   └── versions/     # Scripts de migração\n'
    '├── app/\n'
    '│   ├── api/          # 134 módulos de rota (admin, client, billing, agents, rag, etc.)\n'
    '│   ├── core/         # Config, segurança, logging, métricas\n'
    '│   ├── db/           # Sessão PostgreSQL, Redis, classe base\n'
    '│   ├── domains/      # 15 contextos delimitados (DDD)\n'
    '│   ├── models/       # 105 modelos SQLAlchemy\n'
    '│   ├── schemas/      # Schemas Pydantic para validação\n'
    '│   ├── services/     # 55 módulos de serviço + 70 agentes + 36 roteamento\n'
    '│   ├── utils/        # Utilitários diversos\n'
    '│   └── workers/      # Workers: generation_worker, rag_worker, agent_worker\n'
    '├── tests/            # 53 testes unitários/integração\n'
    '├── requirements.txt  # Dependências Python\n'
    '├── alembic.ini       # Configuração do Alembic\n'
    '└── main.py           # 520 linhas — entry point FastAPI'
)

doc.add_heading('3.3 Contextos Delimitados (DDD)', level=2)
add_table(doc,
    ['Contexto', 'Descrição'],
    [
        ['core_runtime', 'Runtime principal de inferência'],
        ['data_governance', 'Governança de dados e privacidade'],
        ['disaster_recovery', 'Recuperação de desastres e continuidade'],
        ['federation', 'Federação entre instâncias'],
        ['financial', 'Financeiro, billing e faturamento'],
        ['governance', 'Políticas de governança corporativa'],
        ['observability', 'Observabilidade e telemetria'],
        ['operations', 'Operações e remedição'],
        ['plugin_runtime', 'Runtime de plugins'],
        ['runtime', 'Execução e contratos de runtime'],
        ['security', 'Segurança, PKI e atestação'],
        ['sovereign', 'Soberania e air-gap'],
        ['supply_chain', 'Cadeia de suprimentos de modelos'],
        ['trust', 'Confiança e receipts criptográficos'],
    ],
    col_widths=[5, 10]
)

doc.add_heading('3.4 Módulos de API (Rotas)', level=2)
doc.add_paragraph(
    'O sistema possui 134 arquivos de rota em control_plane/app/api/, organizados por domínio:\n\n'
    '• Admin: admin.py, admin_rbac.py, admin_tests.py, admin_models_runtime.py\n'
    '• Comercial: 20+ módulos (commercial_guardrails, routing, federation, capacity, etc.)\n'
    '• Cliente: client.py, portal.py, account\n'
    '• Billing: billing_admin.py, wallet_admin.py, billing_reconciliation_admin.py\n'
    '• Agentes: agent_admin.py, agent_client.py, agent_execution.py, agent_evals.py\n'
    '• RAG: rag.py, rag_enterprise.py\n'
    '• Roteamento: routing_admin.py, routing_test.py, hybrid_admin.py\n'
    '• Segurança: pki_attestation_admin.py, abuse_admin.py\n'
    '• Infra: providers.py, system.py, feature_flags_admin.py, runtime_profiles_admin.py\n'
    '• SDK: public.py (endpoints compatíveis com OpenAI)'
)

doc.add_heading('3.5 Serviços de Agentes', level=2)
doc.add_paragraph(
    'O módulo services/agents/ contém 70 arquivos que implementam a camada de agentes de IA:\n\n'
    '• Ciclo de vida: agent_lifecycle, agent_executor, agent_registry\n'
    '• Memória: agent_memory, agent_memory_tools\n'
    '• Ferramentas: agent_tools, agent_tool_registry, agent_code_interpreter, agent_web_search\n'
    '• Políticas: agent_policies, agent_rbac, agent_slos, agent_observability\n'
    '• Handoffs: agent_handoffs, agent_routing, agent_marketplace\n'
    '• Avaliação: agent_evals, agent_quality\n'
    '• RAG: agent_rag\n'
    '• Cache: prompt_cache\n'
    '• Comunicação: agent_webhook, agent_events'
)

doc.add_heading('3.6 Serviços de Roteamento', level=2)
doc.add_paragraph(
    'O módulo services/routing/ contém 36 arquivos:\n\n'
    '• Roteamento inteligente: smart_routing, routing_strategies, routing_analytics\n'
    '• QoS: quality_of_service, routing_qos\n'
    '• Comercial: commercial_routing, geo_routing, global_traffic_shifting\n'
    '• Liderança: leader_election\n'
    '• Fila: routing_queue, queue_manager\n'
    '• Monitoramento: routing_monitoring, routing_health'
)

# ════════════════════════════════════════════════════
# DATA PLANE
# ════════════════════════════════════════════════════
doc.add_heading('4. Plano de Dados — Data Plane', level=1)

doc.add_heading('4.1 llama.cpp (Produção)', level=2)
doc.add_paragraph(
    '• Engine de inferência principal, compilada com CUDA para aceleração GPU\n'
    '• Multi-stage Docker build (compilação + runtime)\n'
    '• Expõe API compatível com OpenAI: /v1/chat/completions, /v1/models\n'
    '• Suporte a GGUF, flash attention, continuous batching, context shifting\n'
    '• Parâmetros configuráveis: ctx_size, n_gpu_layers, threads, batch_size, ubatch_size, parallel'
)

doc.add_heading('4.2 Mock (Testes)', level=2)
doc.add_paragraph(
    '• Servidor FastAPI simples para testes sem GPU\n'
    '• Endpoints: /v1/models, /v1/chat/completions (streaming e não-streaming)\n'
    '• Usado no perfil fallback-test e em CI'
)

doc.add_heading('4.3 Ollama (Alternativa)', level=2)
doc.add_paragraph(
    '• Perfil opcional para deploy via Ollama\n'
    '• Imagem oficial ollama/ollama:0.9.5 com GPU'
)

# ════════════════════════════════════════════════════
# FRONTEND
# ════════════════════════════════════════════════════
doc.add_heading('5. Frontend', level=1)

doc.add_heading('5.1 Admin Dashboard', level=2)
add_table(doc,
    ['Característica', 'Detalhe'],
    [
        ['Framework', 'React 19'],
        ['Linguagem', 'TypeScript'],
        ['Build', 'Vite 8'],
        ['Estilização', 'Tailwind CSS v4'],
        ['Gráficos', 'Recharts'],
        ['Component Library', 'Storybook'],
        ['Testes', 'Vitest'],
        ['Total de arquivos TS/TSX', '~8.068'],
    ],
    col_widths=[5, 10]
)
doc.add_paragraph(
    'Rotas: dashboard admin, lab de modelos, gerenciamento de clientes, billing, '
    'monitoramento de agentes, configurações de roteamento, métricas em tempo real.'
)

doc.add_heading('5.2 Client Portal', level=2)
doc.add_paragraph(
    '• React 19 + TypeScript + Tailwind CSS v4\n'
    '• Design mobile-first para autoatendimento\n'
    '• Funcionalidades: uso, billing, playground, RAG\n'
    '• Vite 8 como build tool'
)

# ════════════════════════════════════════════════════
# SDKs
# ════════════════════════════════════════════════════
doc.add_heading('6. SDKs Cliente', level=1)
add_table(doc,
    ['SDK', 'Linguagem', 'Dependências', 'Funcionalidades'],
    [
        ['kleberai (Python)', 'Python 3.x', 'httpx', 'Chat, Models, RAG'],
        ['kleberai (Node.js)', 'TypeScript', '—', 'Chat, Models, RAG'],
    ],
    col_widths=[5, 3, 4, 5]
)

# ════════════════════════════════════════════════════
# OPERADOR KUBERNETES
# ════════════════════════════════════════════════════
doc.add_heading('7. Kubernetes Operator', level=1)
doc.add_paragraph(
    '• Implementado com o framework Kopf (Kubernetes Operator Pythonic Framework)\n'
    '• Gerencia o Recurso Customizado (CRD) LLMInferenceStack\n'
    '• Handlers: create, update, delete, resume (lifecycle events)\n'
    '• Atualmente implementa lógica de reconciliação simulada\n'
    '• Chart Helm disponível em deploy/helm/llm-inference-stack/\n'
    '• Manifests K8s brutos em deploy/kubernetes/ (CRDs, deployments, services, configmaps, PVCs)'
)

# ════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ════════════════════════════════════════════════════
doc.add_heading('8. Configurações e Feature Flags', level=1)

doc.add_heading('8.1 Feature Flags', level=2)
doc.add_paragraph(
    'O arquivo config/feature-flags.yaml contém 3.136 feature flags com metadados:\n'
    '• name: identificador único\n'
    '• default: valor padrão (true/false)\n'
    '• owner: time responsável\n'
    '• area: domínio funcional (core, agents, routing, billing, security, etc.)\n'
    '• status: active, internal, deprecated, experimental\n'
    '• introduced_in: versão de introdução\n'
    '• risk_level: low, medium, high\n'
    '• dependencies: flags das quais depende\n'
    '• conflicts: flags com as quais conflita'
)

doc.add_heading('8.2 Modos de Deployment', level=2)
doc.add_paragraph(
    'O sistema suporta 4 modos de deployment:\n'
    '• appliance: modo offline padrão, sem dependência de internet\n'
    '• pilot: implantação piloto controlada\n'
    '• production: produção completa\n'
    '• enterprise_managed: gerenciado enterprise'
)

doc.add_heading('8.3 Perfis de Runtime', level=2)
doc.add_paragraph(
    'Perfis configuráveis em config/runtime-profiles/:\n'
    '• compliance-mode: modo de conformidade (SOC 2, ISO 27001)\n'
    '• managed-hybrid: híbrido gerenciado\n'
    '• sovereign: soberano (air-gap)\n'
    '• entre outros'
)

# ════════════════════════════════════════════════════
# CI/CD
# ════════════════════════════════════════════════════
doc.add_heading('9. CI/CD e Automação', level=1)

doc.add_heading('9.1 GitHub Actions', level=2)
add_table(doc,
    ['Workflow', 'Descrição'],
    [
        ['ci.yml', 'CI principal: lint, testes backend, build frontend, E2E Playwright'],
        ['agent-evals.yml', 'Avaliação de agentes'],
        ['chaos.yml', 'Testes de engenharia de caos'],
        ['compliance.yml', 'Verificações de conformidade'],
        ['deploy-appliance.yml', 'Deploy em appliance'],
        ['deploy-kubernetes.yml', 'Deploy em Kubernetes'],
        ['deploy-pilot.yml', 'Deploy piloto'],
        ['docker-build.yml', 'Build de imagens Docker'],
        ['docs-validation.yml', 'Validação de documentação'],
        ['k8s-validation.yml', 'Validação de manifests K8s'],
        ['release-validation.yml', 'Validação de release'],
        ['security.yml', 'Scan de segurança'],
        ['storybook-docs.yml', 'Build do Storybook/documentação'],
    ],
    col_widths=[5, 12]
)

doc.add_heading('9.2 GitLab CI', level=2)
doc.add_paragraph(
    '11 estágios: preflight → lint → test → security → build → validate → '
    'chaos → package → release'
)

doc.add_heading('9.3 Makefile', level=2)
doc.add_paragraph(
    '• 1.470 linhas de automação\n'
    '• Targets de validação: architecture-boundaries, domain-contracts, adrs, invariants, claims\n'
    '• Validação por fase: phases 66 a 82 (sustainability)\n'
    '• Grupos: CORE_VALIDATION, GOVERNANCE_VALIDATION, RUNTIME_VALIDATION, FEDERATION_VALIDATION'
)

# ════════════════════════════════════════════════════
# TESTES
# ════════════════════════════════════════════════════
doc.add_heading('10. Testes Automatizados', level=1)
doc.add_paragraph(
    'Total de 847 arquivos de teste distribuídos em:\n\n'
    '• tests/: testes de integração/sistema (diversos subdiretórios)\n'
    '• control_plane/tests/: 53 testes unitários/integração do backend\n'
    '• tests/e2e-playwright/: testes E2E com Playwright\n'
    '• tests/agent_evals/: avaliação de agentes\n'
    '• tests/chaos/: engenharia de caos\n'
    '• tests/compliance/: conformidade (SOC 2, ISO 27001)\n'
    '• tests/performance/: baseline de performance\n'
    '• tests/security/: segurança\n'
    '• tests/kubernetes/: deploy K8s\n\n'
    'Markers pytest: quick, slow, release, chaos, k8s\n'
    'Framework: pytest com asyncio_mode = auto'
)

# ════════════════════════════════════════════════════
# COMPLIANCE & GOVERNANÇA
# ════════════════════════════════════════════════════
doc.add_heading('11. Compliance e Governança', level=1)
doc.add_paragraph(
    '• compliance/: evidências SOC 2 e ISO 27001, policies, mapeamentos, riscos, vendors\n'
    '• Config/agent-policies/: políticas padrão para agentes\n'
    '• Config/agent-slo-classes.yaml: definições de SLO para agentes\n'
    '• Config/api-surface.yaml e supported-surface.yaml: inventário da superfície de API\n'
    '• GA Readiness Rules: 12 critérios obrigatórios para GA\n'
    '• Runtime Profiles: compliance-mode com controles específicos\n'
    '• PKI/Atestação: infraestrutura de chave pública e hardware trust'
)

# ════════════════════════════════════════════════════
# SCRIPTS
# ════════════════════════════════════════════════════
doc.add_heading('12. Scripts Operacionais', level=1)
doc.add_paragraph(
    '• 491 scripts (Bash e Python) em scripts/\n'
    '• Automatizam: deploy, backup, restore, validação, testes, release, manutenção\n'
    '• Organizados com scripts/lib/ para bibliotecas compartilhadas\n'
    '• Manifesto em scripts/manifest.yaml'
)

# ════════════════════════════════════════════════════
# CHAOS ENGINEERING
# ════════════════════════════════════════════════════
doc.add_heading('13. Chaos Engineering', level=1)
doc.add_paragraph(
    '• chaos/experiments/: experimentos de caos\n'
    '• chaos/scenarios/: cenários de injeção de falhas\n'
    '• chaos/reports/: relatórios de resultados\n'
    '• Integrado ao CI via GitHub Actions (chaos.yml) e GitLab CI'
)

# ════════════════════════════════════════════════════
# DOCUMENTAÇÃO
# ════════════════════════════════════════════════════
doc.add_heading('14. Documentação', level=1)
doc.add_paragraph(
    '535 arquivos de documentação em docs/:\n'
    '• adr/: Architecture Decision Records\n'
    '• architecture/: Documentação arquitetural\n'
    '• compliance/: Documentação de conformidade\n'
    '• deployments/: Guias de deploy\n'
    '• evals/: Sistema de avaliação\n'
    '• governance/: Governança\n'
    '• integrations/: Integrações\n'
    '• kubernetes/: Deploy K8s\n'
    '• observability/: Observabilidade\n'
    '• operations/: Operações\n'
    '• performance/: Performance\n'
    '• phases/: Fases de implementação (66-82)\n'
    '• platforms/: Plataformas suportadas\n'
    '• plugins/: Sistema de plugins\n'
    '• releases/: Notas de release\n'
    '• rfc/: Request for Comments\n'
    '• runtime/: Documentação de runtime\n'
    '• saas/: Modo SaaS\n'
    '• sdk/: Guias dos SDKs\n'
    '• security/: Segurança\n'
    '• validation/: Validação'
)

# ════════════════════════════════════════════════════
# QUANTIDADE DE ARQUIVOS
# ════════════════════════════════════════════════════
doc.add_heading('15. Métricas do Repositório', level=1)
add_table(doc,
    ['Categoria', 'Quantidade'],
    [
        ['Commits no git', '99'],
        ['Arquivos Python (backend)', '1.107'],
        ['Arquivos TypeScript/TSX (frontend)', '8.068'],
        ['Rotas de API', '134'],
        ['Modelos SQLAlchemy', '105'],
        ['Módulos de serviço', '55'],
        ['Serviços de agente', '70'],
        ['Serviços de roteamento', '36'],
        ['Contextos delimitados', '15'],
        ['Feature flags', '3.136'],
        ['Testes automatizados', '847'],
        ['Scripts operacionais', '491'],
        ['Documentos de documentação', '535'],
        ['Workflows GitHub Actions', '13'],
        ['Estágios GitLab CI', '11'],
        ['Releases empacotadas', '20'],
    ],
    col_widths=[8, 4]
)

# ════════════════════════════════════════════════════
# PRINCIPAIS TECNOLOGIAS
# ════════════════════════════════════════════════════
doc.add_heading('16. Principais Tecnologias', level=1)
add_table(doc,
    ['Tecnologia', 'Uso', 'Versão'],
    [
        ['Python', 'Backend, scripts, testes', '3.12'],
        ['FastAPI', 'Framework REST API', '—'],
        ['SQLAlchemy', 'ORM', '2.0'],
        ['Alembic', 'Migrações de BD', '—'],
        ['Pydantic', 'Validação de dados', 'v2'],
        ['PostgreSQL', 'Banco relacional', '16'],
        ['Redis', 'Cache/fila', '7'],
        ['React', 'Frontend', '19'],
        ['TypeScript', 'Frontend + SDK Node', '—'],
        ['Vite', 'Build tool frontend', '8'],
        ['Tailwind CSS', 'Estilização', 'v4'],
        ['Recharts', 'Gráficos', '—'],
        ['Storybook', 'Component library', '—'],
        ['Playwright', 'Testes E2E', '—'],
        ['llama.cpp', 'Inferência LLM', '—'],
        ['Kopf', 'K8s Operator', '—'],
        ['Prometheus', 'Métricas', 'v2.53.4'],
        ['Grafana', 'Dashboards', '11.1.4'],
        ['Docker', 'Containerização', '—'],
        ['Helm', 'K8s package manager', '—'],
    ],
    col_widths=[4, 6, 3]
)

# ════════════════════════════════════════════════════
# CONSIDERAÇÕES FINAIS
# ════════════════════════════════════════════════════
doc.add_heading('17. Considerações Finais', level=1)
doc.add_paragraph(
    'O LLM Inference Stack é uma plataforma madura e extensivamente modularizada, com clara '
    'separação entre planos de controle e dados, adoção de DDD com contextos delimitados, '
    'mais de 3.000 feature flags para controle granular de funcionalidades, e pipelines de CI/CD '
    'paralelos (GitHub Actions + GitLab CI). A arquitetura orientada a agentes é o diferencial '
    'competitivo, com 70 módulos dedicados ao ciclo de vida, execução, memória, ferramentas, '
    'avaliação e governança de agentes de IA.\n\n'
    'O sistema está na versão v2.0.2-agentic-ga-readiness, indicando preparação para General '
    'Availability com foco em agentes. A plataforma é offline-first, determinística por design '
    '(operações replayáveis e verificáveis), e suporta deployment em appliance, Kubernetes, '
    'ou modo gerenciado enterprise.\n\n'
    'Recomenda-se atenção aos seguintes pontos:\n'
    '• 8.068 arquivos TypeScript/TSX no frontend — possível oportunidade de modularização\n'
    '• 3.136 feature flags — governance robusta, mas requer disciplina de manutenção\n'
    '• 99 commits — repositório relativamente novo ou com squashes frequentes\n'
    '• Dual CI/CD (GitHub + GitLab) — aumenta complexidade operacional'
)

# ── Salvar ──
output_path = '/home/kleber/llm-inference-stack/reports/relatorio_completo_sistema.docx'
doc.save(output_path)
print(f'Relatório salvo em: {output_path}')
