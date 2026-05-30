import { lazy } from 'react'
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
} from 'lucide-react'

// Lazy loaded page components
const Hub = lazy(() => import('./pages/Hub'))
const Clients = lazy(() => import('./pages/Clients'))
const Models = lazy(() => import('./pages/Models'))
const Backends = lazy(() => import('./pages/Backends'))
const Plugins = lazy(() => import('./pages/Plugins'))
const ManagedControlPlane = lazy(() => import('./pages/ManagedControlPlane'))

// Operations
const OperationsOverview = lazy(() => import('./pages/operations/OperationsOverview'))
const RuntimeNodes = lazy(() => import('./pages/operations/RuntimeNodes'))
const ModelRuntime = lazy(() => import('./pages/operations/ModelRuntime'))
const QueueQoS = lazy(() => import('./pages/operations/QueueQoS'))
const Readiness = lazy(() => import('./pages/operations/Readiness'))
const SecurityPosture = lazy(() => import('./pages/operations/SecurityPosture'))
const ReleaseStatus = lazy(() => import('./pages/operations/ReleaseStatus'))
const IncidentTimeline = lazy(() => import('./pages/operations/IncidentTimeline'))

// Performance
const PerformanceDashboard = lazy(() => import('./pages/performance/PerformanceDashboard'))
const BenchmarkHistory = lazy(() => import('./pages/performance/BenchmarkHistory'))
const TuningProfiles = lazy(() => import('./pages/performance/TuningProfiles'))

// Enterprise
const EnterpriseOnboardingDashboard = lazy(() => import('./pages/enterprise/EnterpriseOnboardingDashboard'))
const OnboardingChecklist = lazy(() => import('./pages/enterprise/OnboardingChecklist'))

// Observability
const ObservabilityDashboard = lazy(() => import('./pages/observability/ObservabilityDashboard'))
const RealtimeDashboard = lazy(() => import('./pages/observability/RealtimeDashboard'))
const AgentObservability = lazy(() => import('./pages/observability/AgentObservability'))

// Multi-cluster / Chaos / Compliance
const MultiClusterOverview = lazy(() => import('./pages/multicluster/MultiClusterOverview'))
const ChaosDashboard = lazy(() => import('./pages/chaos/ChaosDashboard'))
const ComplianceOverview = lazy(() => import('./pages/compliance/ComplianceOverview'))
const ControlMap = lazy(() => import('./pages/compliance/ControlMap'))
const EvidenceCenter = lazy(() => import('./pages/compliance/EvidenceCenter'))
const RiskRegister = lazy(() => import('./pages/compliance/RiskRegister'))
const PolicyCenter = lazy(() => import('./pages/compliance/PolicyCenter'))

// Agent Control Plane
const AgentsOverview = lazy(() => import('./pages/agents/AgentsOverview'))
const AgentRegistry = lazy(() => import('./pages/agents/AgentRegistry'))
const AgentRuns = lazy(() => import('./pages/agents/AgentRuns'))
const AgentRunTimeline = lazy(() => import('./pages/agents/AgentRunTimeline'))
const AgentTools = lazy(() => import('./pages/agents/AgentTools'))
const AgentMemory = lazy(() => import('./pages/agents/AgentMemory'))
const AgentApprovals = lazy(() => import('./pages/agents/AgentApprovals'))
const AgentEvals = lazy(() => import('./pages/agents/AgentEvals'))
const AgentPolicies = lazy(() => import('./pages/agents/AgentPolicies'))
const AgentMarketplace = lazy(() => import('./pages/agents/AgentMarketplace'))
const AgentWorkspaces = lazy(() => import('./pages/agents/AgentWorkspaces'))
const AgentArtifactBrowser = lazy(() => import('./pages/agents/AgentArtifactBrowser'))
const AgentArtifactDetail = lazy(() => import('./pages/agents/AgentArtifactDetail'))

// Agent Platform (orphan pages, now connected)
const AgentStudio = lazy(() => import('./pages/agents/studio/AgentStudio'))
const AgentAnalyticsDashboard = lazy(() => import('./pages/agents/analytics/AgentAnalyticsDashboard'))
const ApprovalPortal = lazy(() => import('./pages/agents/approvals/ApprovalPortal'))
const AgentPromotion = lazy(() => import('./pages/agents/AgentPromotion'))
const AgentLineage = lazy(() => import('./pages/agents/AgentLineage'))

// Collaboration / Dev tools
const CollaborativeChat = lazy(() => import('./pages/chat/CollaborativeChat'))
const WebIDE = lazy(() => import('./pages/ide/WebIDE'))
const DeveloperPortal = lazy(() => import('./pages/developers/DeveloperPortal'))

export interface RouteConfig {
  path: string
  component: React.LazyExoticComponent<React.FC<Record<string, unknown>>>
  label: string
  icon: LucideIcon
  group: string
  /** If true, shows a "Disabled" badge in Hub and sidebar */
  disabled?: boolean
  /** If true, hidden from sidebar but still routable */
  hidden?: boolean
}

export const routes: RouteConfig[] = [
  // ── Core ──────────────────────────────────────────
  { path: '/', component: Hub, label: 'Hub', icon: LayoutDashboard, group: 'core' },
  { path: '/clients', component: Clients, label: 'Clientes', icon: Users, group: 'core' },
  { path: '/models', component: Models, label: 'Modelos', icon: Box, group: 'core' },
  { path: '/backends', component: Backends, label: 'Backends', icon: Server, group: 'core' },
  { path: '/plugins', component: Plugins, label: 'Plugins', icon: Zap, group: 'core' },
  { path: '/saas', component: ManagedControlPlane, label: 'SaaS', icon: Cloud, group: 'core' },

  // ── Operations ────────────────────────────────────
  { path: '/operations', component: OperationsOverview, label: 'Operações', icon: Activity, group: 'operations' },
  { path: '/operations/nodes', component: RuntimeNodes, label: 'Runtime Nodes', icon: Server, group: 'operations', hidden: true },
  { path: '/operations/runtime', component: ModelRuntime, label: 'Model Runtime', icon: Activity, group: 'operations', hidden: true },
  { path: '/operations/qos', component: QueueQoS, label: 'Queue QoS', icon: Activity, group: 'operations', hidden: true },
  { path: '/operations/readiness', component: Readiness, label: 'Readiness', icon: ShieldCheck, group: 'operations', hidden: true },
  { path: '/operations/security', component: SecurityPosture, label: 'Security', icon: Shield, group: 'operations', hidden: true },
  { path: '/operations/release', component: ReleaseStatus, label: 'Release Status', icon: Rocket, group: 'operations', hidden: true },
  { path: '/operations/incidents', component: IncidentTimeline, label: 'Incidents', icon: ShieldAlert, group: 'operations', hidden: true },

  // ── Performance ───────────────────────────────────
  { path: '/performance', component: PerformanceDashboard, label: 'Performance', icon: TrendingUp, group: 'performance' },
  { path: '/performance/history', component: BenchmarkHistory, label: 'Benchmark History', icon: BarChart3, group: 'performance', hidden: true },
  { path: '/performance/profiles', component: TuningProfiles, label: 'Tuning Profiles', icon: Wrench, group: 'performance', hidden: true },

  // ── Enterprise ────────────────────────────────────
  { path: '/enterprise/onboarding', component: EnterpriseOnboardingDashboard, label: 'Enterprise Onboarding', icon: Briefcase, group: 'enterprise' },
  { path: '/enterprise/onboarding/:id', component: OnboardingChecklist, label: 'Onboarding Checklist', icon: Briefcase, group: 'enterprise', hidden: true },

  // ── Observability ─────────────────────────────────
  { path: '/observability', component: ObservabilityDashboard, label: 'Observabilidade', icon: Monitor, group: 'observability' },
  { path: '/observability/realtime', component: RealtimeDashboard, label: 'Monitoramento Live', icon: Activity, group: 'observability', hidden: true },
  { path: '/observability/agents', component: AgentObservability, label: 'Agent Observability', icon: Bot, group: 'observability', hidden: true },

  // ── Enterprise Advanced ───────────────────────────
  { path: '/multicluster', component: MultiClusterOverview, label: 'Multi-Cluster', icon: Network, group: 'advanced', disabled: true },
  { path: '/chaos', component: ChaosDashboard, label: 'Chaos Engineering', icon: FlaskConical, group: 'advanced', disabled: true },

  // ── Compliance ────────────────────────────────────
  { path: '/compliance', component: ComplianceOverview, label: 'Compliance', icon: Gavel, group: 'compliance' },
  { path: '/compliance/controls', component: ControlMap, label: 'Control Map', icon: Gavel, group: 'compliance', hidden: true },
  { path: '/compliance/evidence', component: EvidenceCenter, label: 'Evidence Center', icon: Gavel, group: 'compliance', hidden: true },
  { path: '/compliance/risks', component: RiskRegister, label: 'Risk Register', icon: Gavel, group: 'compliance', hidden: true },
  { path: '/compliance/policies', component: PolicyCenter, label: 'Policy Center', icon: Gavel, group: 'compliance', hidden: true },

  // ── Agent Control Plane ───────────────────────────
  { path: '/agents', component: AgentsOverview, label: 'Agentes', icon: Bot, group: 'agents' },
  { path: '/agents/registry', component: AgentRegistry, label: 'Registry', icon: Box, group: 'agents', hidden: true },
  { path: '/agents/runs', component: AgentRuns, label: 'Runs', icon: Activity, group: 'agents', hidden: true },
  { path: '/agents/runs/:id', component: AgentRunTimeline, label: 'Run Timeline', icon: Activity, group: 'agents', hidden: true },
  { path: '/agents/tools', component: AgentTools, label: 'Tools', icon: Wrench, group: 'agents', hidden: true },
  { path: '/agents/memory', component: AgentMemory, label: 'Memory', icon: Bot, group: 'agents', hidden: true },
  { path: '/agents/approvals', component: AgentApprovals, label: 'Approvals', icon: ShieldCheck, group: 'agents', hidden: true },
  { path: '/agents/evals', component: AgentEvals, label: 'Evals', icon: FlaskConical, group: 'agents', hidden: true },
  { path: '/agents/policies', component: AgentPolicies, label: 'Policies', icon: Shield, group: 'agents', hidden: true },
  { path: '/agents/marketplace', component: AgentMarketplace, label: 'Marketplace', icon: Zap, group: 'agents', hidden: true },
  { path: '/agents/workspaces', component: AgentWorkspaces, label: 'Workspaces', icon: Code2, group: 'agents', hidden: true },
  { path: '/agents/workspaces/:id', component: AgentArtifactBrowser, label: 'Artifact Browser', icon: Code2, group: 'agents', hidden: true },
  { path: '/agents/workspaces/:id/artifacts/:artifactId', component: AgentArtifactDetail, label: 'Artifact Detail', icon: Code2, group: 'agents', hidden: true },

  // ── Agent Platform (orphan pages, NOW CONNECTED) ──
  { path: '/agents/studio', component: AgentStudio, label: 'Agent Studio', icon: Wrench, group: 'agents' },
  { path: '/agents/analytics', component: AgentAnalyticsDashboard, label: 'Analytics', icon: BarChart3, group: 'agents' },
  { path: '/agents/approvals-portal', component: ApprovalPortal, label: 'Approval Portal', icon: Inbox, group: 'agents' },
  { path: '/agents/promotion', component: AgentPromotion, label: 'Promotion', icon: Rocket, group: 'agents' },
  { path: '/agents/lineage', component: AgentLineage, label: 'Lineage', icon: GitBranch, group: 'agents' },

  // ── Collaboration ─────────────────────────────────
  { path: '/agents/chat', component: CollaborativeChat, label: 'Chat Colaborativo', icon: MessageSquare, group: 'agents' },

  // ── Developer Tools ───────────────────────────────
  { path: '/ide', component: WebIDE, label: 'Web IDE', icon: Code2, group: 'developers' },
  { path: '/developers', component: DeveloperPortal, label: 'Developer Portal', icon: Key, group: 'developers' },

  // ── Placeholder routes (no page yet) ──────────────
  // These will render a ComingSoon stub
]

/** Routes that have no real page yet - will show ComingSoon */
export const placeholderRoutes: Array<{ path: string; label: string; icon: LucideIcon; group: string; description: string }> = [
  { path: '/api-keys', label: 'API Keys', icon: Key, group: 'core', description: 'Emissão, rotação e governança de credenciais.' },
  { path: '/billing', label: 'Billing', icon: Wallet, group: 'core', description: 'Planos, pricing e cobrança.' },
  { path: '/usage', label: 'Uso', icon: TrendingUp, group: 'core', description: 'Consumo por cliente e métricas agregadas.' },
  { path: '/rag', label: 'RAG', icon: FileText, group: 'core', description: 'Vaults e documentos da camada RAG.' },
  { path: '/security', label: 'Segurança', icon: Shield, group: 'core', description: 'Auditoria e eventos de segurança.' },
  { path: '/reports', label: 'Relatórios', icon: FileText, group: 'core', description: 'Relatórios executivos e exportações.' },
  { path: '/settings', label: 'Configurações', icon: Settings, group: 'core', description: 'Configuração geral do sistema.' },
]

/**
 * Sidebar navigation structure.
 * Groups are ordered. Items within a group appear in the sidebar.
 */
export interface SidebarGroup {
  key: string
  label: string
  icon: LucideIcon
  items: RouteConfig[]
}

export function buildSidebarGroups(): SidebarGroup[] {
  const byGroup = new Map<string, RouteConfig[]>()
  for (const r of routes) {
    if (r.hidden || r.path === '/') continue
    const arr = byGroup.get(r.group) || []
    arr.push(r)
    byGroup.set(r.group, arr)
  }

  const groupMeta: Record<string, { label: string; icon: LucideIcon }> = {
    core: { label: 'Core', icon: LayoutDashboard },
    operations: { label: 'Operations', icon: Activity },
    performance: { label: 'Performance', icon: TrendingUp },
    enterprise: { label: 'Enterprise', icon: Briefcase },
    observability: { label: 'Observability', icon: Monitor },
    advanced: { label: 'Advanced', icon: Network },
    compliance: { label: 'Compliance', icon: Gavel },
    agents: { label: 'Agentic Platform', icon: Bot },
    developers: { label: 'Developers', icon: Code2 },
  }

  const order = ['core', 'agents', 'operations', 'performance', 'enterprise', 'observability', 'compliance', 'advanced', 'developers']
  const groups: SidebarGroup[] = []
  for (const key of order) {
    const items = byGroup.get(key)
    if (!items || items.length === 0) continue
    const meta = groupMeta[key] || { label: key, icon: LayoutDashboard }
    groups.push({ key, label: meta.label, icon: meta.icon, items })
  }
  return groups
}
