import type { LucideIcon } from 'lucide-react'
import {
  LayoutDashboard,
  Users,
  Box,
  Server,
  Zap,
  Cloud,
  Activity,
  Bot,
  Wrench,
  FlaskConical,
  ShieldCheck,
  BarChart3,
  MessageSquare,
  Code2,
  Key,
  Briefcase,
  Monitor,
  Network,
  Gavel,
  Settings,
  FileText,
  Wallet,
  TrendingUp,
  Shield,
  GitBranch,
  Rocket,
  Inbox,
  Package,
} from 'lucide-react'

export type FeatureFlag =
  | 'agents'
  | 'operations'
  | 'performance'
  | 'enterprise'
  | 'observability'
  | 'compliance'
  | 'advanced'
  | 'developers'
  | 'voice'
  | 'studio'
  | 'chat'
  | 'ide'

export type RouteStatus = 'active' | 'beta' | 'coming_soon' | 'disabled'

export interface NavRoute {
  path: string
  label: string
  icon: LucideIcon
  section: string
  featureFlag: FeatureFlag
  status: RouteStatus
  /** If true, hidden from sidebar but still routable */
  hidden?: boolean
  /** If true, not shown in sidebar at all */
  sidebarHidden?: boolean
  /** Breadcrumb override (defaults to label) */
  breadcrumb?: string
  /** Parent path for nested breadcrumbs */
  parentPath?: string
}

// ── Route Registry ────────────────────────────────────────────────

export const navRoutes: NavRoute[] = [
  // ── Core ──────────────────────────────────────────────
  { path: '/', label: 'Hub', icon: LayoutDashboard, section: 'core', featureFlag: 'agents', status: 'active', sidebarHidden: true },
  { path: '/clients', label: 'Clientes', icon: Users, section: 'core', featureFlag: 'agents', status: 'active' },
  { path: '/models', label: 'Modelos', icon: Box, section: 'core', featureFlag: 'agents', status: 'active' },
  { path: '/backends', label: 'Backends', icon: Server, section: 'core', featureFlag: 'agents', status: 'active' },
  { path: '/plugins', label: 'Plugins', icon: Zap, section: 'core', featureFlag: 'agents', status: 'active' },
  { path: '/saas', label: 'SaaS', icon: Cloud, section: 'core', featureFlag: 'agents', status: 'active' },

  // ── Agentic Platform ──────────────────────────────────
  { path: '/agents', label: 'Agentes', icon: Bot, section: 'agents', featureFlag: 'agents', status: 'active' },
  { path: '/agents/registry', label: 'Registry', icon: Box, section: 'agents', featureFlag: 'agents', status: 'active', hidden: true, parentPath: '/agents' },
  { path: '/agents/runs', label: 'Runs', icon: Activity, section: 'agents', featureFlag: 'agents', status: 'active', hidden: true, parentPath: '/agents' },
  { path: '/agents/runs/:id', label: 'Run Timeline', icon: Activity, section: 'agents', featureFlag: 'agents', status: 'active', hidden: true, parentPath: '/agents/runs' },
  { path: '/agents/tools', label: 'Tools', icon: Wrench, section: 'agents', featureFlag: 'agents', status: 'active', hidden: true, parentPath: '/agents' },
  { path: '/agents/memory', label: 'Memory', icon: Bot, section: 'agents', featureFlag: 'agents', status: 'active', hidden: true, parentPath: '/agents' },
  { path: '/agents/approvals', label: 'Approvals', icon: ShieldCheck, section: 'agents', featureFlag: 'agents', status: 'active', hidden: true, parentPath: '/agents' },
  { path: '/agents/evals', label: 'Evals', icon: FlaskConical, section: 'agents', featureFlag: 'agents', status: 'active', hidden: true, parentPath: '/agents' },
  { path: '/agents/policies', label: 'Policies', icon: Shield, section: 'agents', featureFlag: 'agents', status: 'active', hidden: true, parentPath: '/agents' },
  { path: '/agents/marketplace', label: 'Marketplace', icon: Zap, section: 'agents', featureFlag: 'agents', status: 'active', hidden: true, parentPath: '/agents' },
  { path: '/agents/workspaces', label: 'Workspaces', icon: Code2, section: 'agents', featureFlag: 'agents', status: 'active', hidden: true, parentPath: '/agents' },
  { path: '/agents/workspaces/:id', label: 'Artifact Browser', icon: Code2, section: 'agents', featureFlag: 'agents', status: 'active', hidden: true, parentPath: '/agents/workspaces' },
  { path: '/agents/workspaces/:id/artifacts/:artifactId', label: 'Artifact Detail', icon: Code2, section: 'agents', featureFlag: 'agents', status: 'active', hidden: true, parentPath: '/agents/workspaces/:id' },
  { path: '/agents/studio', label: 'Agent Studio', icon: Wrench, section: 'agents', featureFlag: 'studio', status: 'active' },
  { path: '/agents/analytics', label: 'Analytics', icon: BarChart3, section: 'agents', featureFlag: 'agents', status: 'active' },
  { path: '/agents/approvals-portal', label: 'Approval Portal', icon: Inbox, section: 'agents', featureFlag: 'agents', status: 'active' },
  { path: '/agents/promotion', label: 'Promotion', icon: Rocket, section: 'agents', featureFlag: 'agents', status: 'beta' },
  { path: '/agents/lineage', label: 'Lineage', icon: GitBranch, section: 'agents', featureFlag: 'agents', status: 'beta' },
  { path: '/agents/chat', label: 'Chat Colaborativo', icon: MessageSquare, section: 'agents', featureFlag: 'chat', status: 'active' },

  // ── Operations ────────────────────────────────────────
  { path: '/operations', label: 'Operacoes', icon: Activity, section: 'operations', featureFlag: 'operations', status: 'active' },
  { path: '/operations/nodes', label: 'Runtime Nodes', icon: Server, section: 'operations', featureFlag: 'operations', status: 'active', hidden: true, parentPath: '/operations' },
  { path: '/operations/runtime', label: 'Model Runtime', icon: Activity, section: 'operations', featureFlag: 'operations', status: 'active', hidden: true, parentPath: '/operations' },
  { path: '/operations/qos', label: 'Queue QoS', icon: Activity, section: 'operations', featureFlag: 'operations', status: 'active', hidden: true, parentPath: '/operations' },
  { path: '/operations/readiness', label: 'Readiness', icon: ShieldCheck, section: 'operations', featureFlag: 'operations', status: 'active', hidden: true, parentPath: '/operations' },
  { path: '/operations/security', label: 'Security', icon: Shield, section: 'operations', featureFlag: 'operations', status: 'active', hidden: true, parentPath: '/operations' },
  { path: '/operations/release', label: 'Release Status', icon: Rocket, section: 'operations', featureFlag: 'operations', status: 'active', hidden: true, parentPath: '/operations' },
  { path: '/operations/incidents', label: 'Incidents', icon: ShieldCheck, section: 'operations', featureFlag: 'operations', status: 'active', hidden: true, parentPath: '/operations' },

  // ── Performance ───────────────────────────────────────
  { path: '/performance', label: 'Performance', icon: TrendingUp, section: 'performance', featureFlag: 'performance', status: 'active' },
  { path: '/performance/history', label: 'Benchmark History', icon: BarChart3, section: 'performance', featureFlag: 'performance', status: 'active', hidden: true, parentPath: '/performance' },
  { path: '/performance/profiles', label: 'Tuning Profiles', icon: Wrench, section: 'performance', featureFlag: 'performance', status: 'active', hidden: true, parentPath: '/performance' },

  // ── Enterprise ────────────────────────────────────────
  { path: '/enterprise/onboarding', label: 'Enterprise Onboarding', icon: Briefcase, section: 'enterprise', featureFlag: 'enterprise', status: 'active' },
  { path: '/enterprise/onboarding/:id', label: 'Onboarding Checklist', icon: Briefcase, section: 'enterprise', featureFlag: 'enterprise', status: 'active', hidden: true, parentPath: '/enterprise/onboarding' },

  // ── Observability ─────────────────────────────────────
  { path: '/observability', label: 'Observabilidade', icon: Monitor, section: 'observability', featureFlag: 'observability', status: 'active' },
  { path: '/observability/realtime', label: 'Monitoramento Live', icon: Activity, section: 'observability', featureFlag: 'observability', status: 'active', hidden: true, parentPath: '/observability' },
  { path: '/observability/agents', label: 'Agent Observability', icon: Bot, section: 'observability', featureFlag: 'observability', status: 'active', hidden: true, parentPath: '/observability' },

  // ── Advanced ──────────────────────────────────────────
  { path: '/multicluster', label: 'Multi-Cluster', icon: Network, section: 'advanced', featureFlag: 'advanced', status: 'active' },
  { path: '/chaos', label: 'Chaos Engineering', icon: FlaskConical, section: 'advanced', featureFlag: 'advanced', status: 'active' },

  // ── Compliance ────────────────────────────────────────
  { path: '/compliance', label: 'Compliance', icon: Gavel, section: 'compliance', featureFlag: 'compliance', status: 'active' },
  { path: '/compliance/controls', label: 'Control Map', icon: Gavel, section: 'compliance', featureFlag: 'compliance', status: 'active', hidden: true, parentPath: '/compliance' },
  { path: '/compliance/evidence', label: 'Evidence Center', icon: Gavel, section: 'compliance', featureFlag: 'compliance', status: 'active', hidden: true, parentPath: '/compliance' },
  { path: '/compliance/risks', label: 'Risk Register', icon: Gavel, section: 'compliance', featureFlag: 'compliance', status: 'active', hidden: true, parentPath: '/compliance' },
  { path: '/compliance/policies', label: 'Policy Center', icon: Gavel, section: 'compliance', featureFlag: 'compliance', status: 'active', hidden: true, parentPath: '/compliance' },

  // ── Developers ────────────────────────────────────────
  { path: '/ide', label: 'Web IDE', icon: Code2, section: 'developers', featureFlag: 'ide', status: 'active' },
  { path: '/developers', label: 'Developer Portal', icon: Key, section: 'developers', featureFlag: 'developers', status: 'active' },
  { path: '/developers/bundles', label: 'Agent Bundles', icon: Package, section: 'developers', featureFlag: 'developers', status: 'active' },
  { path: '/prompts', label: 'Prompts', icon: FileText, section: 'developers', featureFlag: 'developers', status: 'active' },

  // ── Business and governance surfaces ──────────────────
  { path: '/api-keys', label: 'API Keys', icon: Key, section: 'core', featureFlag: 'agents', status: 'active' },
  { path: '/billing', label: 'Billing', icon: Wallet, section: 'core', featureFlag: 'agents', status: 'active' },
  { path: '/usage', label: 'Uso', icon: TrendingUp, section: 'core', featureFlag: 'agents', status: 'active' },
  { path: '/rag', label: 'RAG', icon: FileText, section: 'core', featureFlag: 'agents', status: 'active' },
  { path: '/security', label: 'Seguranca', icon: Shield, section: 'core', featureFlag: 'agents', status: 'active' },
  { path: '/reports', label: 'Relatorios', icon: FileText, section: 'core', featureFlag: 'agents', status: 'active' },
  { path: '/settings', label: 'Configuracoes', icon: Settings, section: 'core', featureFlag: 'agents', status: 'active' },
]

// ── Section Metadata ─────────────────────────────────────────────

export interface NavSection {
  key: string
  label: string
  icon: LucideIcon
  featureFlag: FeatureFlag
}

export const navSections: NavSection[] = [
  { key: 'core', label: 'Core', icon: LayoutDashboard, featureFlag: 'agents' },
  { key: 'agents', label: 'Agentic Platform', icon: Bot, featureFlag: 'agents' },
  { key: 'operations', label: 'Operations', icon: Activity, featureFlag: 'operations' },
  { key: 'performance', label: 'Performance', icon: TrendingUp, featureFlag: 'performance' },
  { key: 'enterprise', label: 'Enterprise', icon: Briefcase, featureFlag: 'enterprise' },
  { key: 'observability', label: 'Observability', icon: Monitor, featureFlag: 'observability' },
  { key: 'compliance', label: 'Compliance', icon: Gavel, featureFlag: 'compliance' },
  { key: 'advanced', label: 'Advanced', icon: Network, featureFlag: 'advanced' },
  { key: 'developers', label: 'Developers', icon: Code2, featureFlag: 'developers' },
]

// ── Hub Card Metadata ────────────────────────────────────────────

export interface HubCardMeta {
  badge: string
  description: string
}

export const hubCardMeta: Record<string, HubCardMeta> = {
  '/clients': { badge: 'Core', description: 'Gestao de contas, tenants e dados principais de clientes.' },
  '/models': { badge: 'Runtime', description: 'Catalogo de modelos, aliases, defaults e controles operacionais.' },
  '/backends': { badge: 'Runtime', description: 'Integracoes de inferencia, providers e estado do backend.' },
  '/plugins': { badge: 'Runtime', description: 'Marketplace de plugins e extensoes do sistema.' },
  '/saas': { badge: 'SaaS', description: 'Managed control plane para deployments SaaS.' },
  '/agents': { badge: 'Agents', description: 'Agentes IA, registry, runs, tools e politicas.' },
  '/agents/studio': { badge: 'Agents', description: 'Visual flow editor para construir e depurar agentes.' },
  '/agents/analytics': { badge: 'Agents', description: 'Metricas de latencia, custo e uso de ferramentas dos agentes.' },
  '/agents/approvals-portal': { badge: 'Agents', description: 'Portal de aprovacao humana para acoes de agentes.' },
  '/agents/promotion': { badge: 'Agents', description: 'Promocao de agentes entre ambientes.' },
  '/agents/lineage': { badge: 'Agents', description: 'Historico de versoes e linhagem de agentes.' },
  '/agents/chat': { badge: 'Collab', description: 'Chat colaborativo com mencoes de agentes em tempo real.' },
  '/operations': { badge: 'Ops', description: 'Overview operacional, nos de runtime, readiness e remediacao.' },
  '/performance': { badge: 'Tuning', description: 'Benchmark de runtime, recomendacoes de IA e perfis de otimizacao.' },
  '/enterprise/onboarding': { badge: 'Success', description: 'Gestao de pilotos, checklists enterprise e relatorios de handover.' },
  '/observability': { badge: 'Advanced', description: 'Dashboards Grafana, orcamentos de erro (SLO) e timeline de incidentes.' },
  '/compliance': { badge: 'Enterprise', description: 'Preparacao para SOC 2 e ISO 27001 com evidencias auditaveis.' },
  '/ide': { badge: 'Dev', description: 'IDE web para edicao de agentes, plugins e manifests.' },
  '/developers': { badge: 'Dev', description: 'Portal do desenvolvedor com API keys, CLI e templates.' },
  '/developers/bundles': { badge: 'Dev', description: 'Criar, validar, assinar e publicar bundles de agentes.' },
  '/prompts': { badge: 'Dev', description: 'Criacao, versionamento e gestao de templates de prompts.' },
  '/api-keys': { badge: 'Core', description: 'Emissao, rotacao e governanca de credenciais.' },
  '/billing': { badge: 'Finance', description: 'Planos, pricing e cobranca.' },
  '/usage': { badge: 'Analytics', description: 'Consumo por cliente e metricas agregadas.' },
  '/rag': { badge: 'Data', description: 'Vaults e documentos da camada RAG.' },
  '/security': { badge: 'Risk', description: 'Auditoria e eventos de seguranca.' },
  '/reports': { badge: 'Ops', description: 'Relatorios executivos e exportacoes.' },
  '/settings': { badge: 'System', description: 'Configuracao geral do sistema.' },
  '/multicluster': { badge: 'Enterprise', description: 'Gestao multi-cluster e failover orquestrado.' },
  '/chaos': { badge: 'Experimental', description: 'Injecao controlada de falhas para validar resiliencia.' },
}

// ── Helpers ──────────────────────────────────────────────────────

/** Get sidebar-visible routes for a section */
export function getSectionRoutes(sectionKey: string): NavRoute[] {
  return navRoutes.filter(
    r => r.section === sectionKey && !r.hidden && !r.sidebarHidden
  )
}

/** Get a route by path */
export function getRouteByPath(path: string): NavRoute | undefined {
  return navRoutes.find(r => r.path === path)
}

/** Build breadcrumb trail from path */
export function buildBreadcrumbs(pathname: string): Array<{ label: string; path: string }> {
  if (pathname === '/') return []

  const crumbs: Array<{ label: string; path: string }> = []
  const segments = pathname.split('/').filter(Boolean)
  let acc = ''

  for (const seg of segments) {
    acc += '/' + seg
    const route = navRoutes.find(r => r.path === acc)
    crumbs.push({
      label: route?.label || seg.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      path: acc,
    })
  }

  return crumbs
}

/** Check if a route status shows as disabled/coming soon */
export function isRouteDisabled(status: RouteStatus): boolean {
  return status === 'coming_soon' || status === 'disabled'
}
