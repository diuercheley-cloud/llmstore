import { lazy } from 'react'
import { navConfig, type NavRoute, sectionMeta, type RouteStatus } from '../navigation/navConfig'
import type { LucideIcon } from 'lucide-react'
import { LayoutDashboard } from 'lucide-react'

// ── Lazy Component Map ────────────────────────────────────────────

const componentMap: Record<string, React.LazyExoticComponent<React.ComponentType<any>>> = {
  '/': lazy(() => import('../pages/Hub')),
  '/clients': lazy(() => import('../pages/Clients')),
  '/models': lazy(() => import('../pages/Models')),
  '/backends': lazy(() => import('../pages/Backends')),
  '/multimodal': lazy(() => import('../pages/multimodal/MultimodalManagement')),
  '/plugins': lazy(() => import('../pages/Plugins')),
  '/saas': lazy(() => import('../pages/ManagedControlPlane')),
  '/api-keys': lazy(() => import('../pages/api-keys/ApiKeys')),
  '/rbac': lazy(() => import('../pages/rbac/RbacManagement')),
  '/approvals': lazy(() => import('../pages/Approvals')),
  '/billing': lazy(() => import('../pages/billing/Billing')),
  '/billing/costs': lazy(() => import('../pages/billing/CostAttribution')),
  '/billing/reconciliation': lazy(() => import('../pages/billing/Reconciliation')),
  '/billing/disputes': lazy(() => import('../pages/billing/Disputes')),
  '/usage': lazy(() => import('../pages/usage/Usage')),
  '/rag': lazy(() => import('../pages/rag/Rag')),
  '/security': lazy(() => import('../pages/security/Security')),
  '/reports': lazy(() => import('../pages/reports/Reports')),
  '/settings': lazy(() => import('../pages/settings/Settings')),

  '/modules': lazy(() => import('../pages/Hub')),
  '/compliance': lazy(() => import('../pages/compliance/ComplianceOverview')),
  '/compliance/dlp': lazy(() => import('../pages/compliance/DlpDashboard')),
  '/governance/policy': lazy(() => import('../pages/governance/PolicyEngine')),
  '/security/abuse': lazy(() => import('../pages/security/AbuseMonitoring')),
  '/compliance/controls': lazy(() => import('../pages/compliance/ControlMap')),
  '/compliance/risks': lazy(() => import('../pages/compliance/RiskRegister')),
  '/compliance/policies': lazy(() => import('../pages/compliance/PolicyCenter')),
  '/compliance/evidence': lazy(() => import('../pages/compliance/EvidenceCenter')),
  
  '/observability': lazy(() => import('../pages/observability/ObservabilityDashboard')),
  '/observability/agents': lazy(() => import('../pages/observability/AgentObservability')),
  '/observability/advanced': lazy(() => import('../pages/observability/AdvancedObservability')),
  '/performance': lazy(() => import('../pages/performance/Performance')),
  '/performance/arena': lazy(() => import('../pages/performance/EvaluationArena')),
  '/performance/history': lazy(() => import('../pages/performance/BenchmarkHistory')),
  '/performance/profiles': lazy(() => import('../pages/performance/TuningProfiles')),
  '/enterprise/onboarding': lazy(() => import('../pages/enterprise/EnterpriseOnboardingDashboard')),
  '/enterprise/checklist': lazy(() => import('../pages/enterprise/OnboardingChecklist')),
  '/enterprise/checklist/:id': lazy(() => import('../pages/enterprise/OnboardingChecklist')),

  '/agents': lazy(() => import('../pages/agents/AgentsOverview')),
  '/agents/protocols': lazy(() => import('../pages/agents/AgentProtocols')),
  '/agents/studio': lazy(() => import('../pages/agents/studio/AgentStudio')),
  '/agents/memory': lazy(() => import('../pages/agents/AgentMemory')),
  '/agents/tools': lazy(() => import('../pages/agents/AgentTools')),
  '/agents/routing': lazy(() => import('../pages/agents/AgentRouting')),
  '/agents/readiness': lazy(() => import('../pages/agents/AgentReadiness')),
  '/agents/teams': lazy(() => import('../pages/agents/AgentTeams')),
  '/agents/workflow-ops': lazy(() => import('../pages/agents/AgentWorkflowOps')),
  '/agents/runs': lazy(() => import('../pages/agents/AgentRuns')),
  '/agents/marketplace': lazy(() => import('../pages/marketplace/Marketplace')),
  '/agents/analytics': lazy(() => import('../pages/agents/analytics/AgentAnalyticsDashboard')),
  '/agents/approvals': lazy(() => import('../pages/agents/approvals/ApprovalPortal')),
  '/agents/runs/:id': lazy(() => import('../pages/agents/AgentRunTimeline')),
  '/agents/workspaces/:id': lazy(() => import('../pages/agents/AgentArtifactBrowser')),
  '/agents/workspaces/:id/artifacts/:artifactId': lazy(() => import('../pages/agents/AgentArtifactDetail')),
  '/agents/chat': lazy(() => import('../pages/chat/CollaborativeChat')),
  '/agents/promotion': lazy(() => import('../pages/agents/AgentPromotion')),
  '/agents/lineage': lazy(() => import('../pages/agents/AgentLineage')),
  '/agents/mcp': lazy(() => import('../pages/agents/mcp/MCPDashboard')),
  '/agents/deployments': lazy(() => import('../pages/agents/deployments/DeploymentsOverview')),
  '/agents/kg': lazy(() => import('../pages/agents/kg/KnowledgeGraph')),
  '/agents/optimization': lazy(() => import('../pages/agents/optimization/OptimizationTournaments')),
  '/agents/evaluation': lazy(() => import('../pages/agents/AgentEvaluation')),
  '/agents/registry': lazy(() => import('../pages/agents/AgentRegistry')),
  '/agents/workspaces': lazy(() => import('../pages/agents/AgentWorkspaces')),

  '/operations': lazy(() => import('../pages/operations/OperationsOverview')),
  '/operations/runtime-nodes': lazy(() => import('../pages/operations/RuntimeNodes')),
  '/operations/profile': lazy(() => import('../pages/operations/SystemProfile')),
  '/operations/gpu': lazy(() => import('../pages/operations/GPUAutoscaling')),
  '/operations/adapters': lazy(() => import('../pages/operations/AdapterRegistry')),
  '/operations/inference': lazy(() => import('../pages/operations/InferenceBackends')),
  '/operations/readiness': lazy(() => import('../pages/operations/Readiness')),
  '/operations/security': lazy(() => import('../pages/operations/SecurityPosture')),
  '/operations/backups': lazy(() => import('../pages/operations/BackupDashboard')),
  '/operations/aiops': lazy(() => import('../pages/operations/AIOpsDashboard')),
  '/operations/workflow-governance': lazy(() => import('../pages/operations/WorkflowGovernance')),
  '/operations/model-supply-chain': lazy(() => import('../pages/operations/ModelSupplyChain')),


  '/ide': lazy(() => import('../pages/ide/WebIDE')),
  '/developers': lazy(() => import('../pages/developers/DeveloperPortal')),
  '/developers/bundles': lazy(() => import('../pages/developers/Bundles')),
  '/prompts': lazy(() => import('../pages/prompts/Prompts')),

  '/multicluster': lazy(() => import('../pages/multicluster/MultiClusterOverview')),
  '/advanced/federation': lazy(() => import('../pages/advanced/FederationOverview')),
  '/chaos': lazy(() => import('../pages/chaos/ChaosDashboard')),

  // New modules
  '/operations/mlops': lazy(() => import('../pages/mlops/MLOpsDashboard')),
  '/rag/vectorstores': lazy(() => import('../pages/rag/VectorStores')),
  '/agents/worker-dlq': lazy(() => import('../pages/agents/WorkerDLQ')),
  '/agents/code-interpreter': lazy(() => import('../pages/agents/CodeInterpreterAdmin')),
  '/compliance/attestation': lazy(() => import('../pages/compliance/Attestation')),
  '/governance/sovereign': lazy(() => import('../pages/governance/SovereignGovernance')),
}

export { type RouteStatus } from '../navigation/navConfig'

export interface RouteConfig extends NavRoute {
  component: React.LazyExoticComponent<React.ComponentType<any>>
}

export const routes: RouteConfig[] = navConfig.map(nav => ({
  ...nav,
  component: componentMap[nav.path] || lazy(() => import('../components/ui-feedback').then(m => ({ default: m.NotFound })))
})).concat([
  {
    label: 'Checklist',
    path: '/enterprise/checklist/:id',
    icon: navConfig.find(route => route.path === '/enterprise/checklist')?.icon || LayoutDashboard,
    section: 'enterprise',
    status: 'active',
    description: 'Checklist de prontidão para produção Enterprise.',
    hidden: true,
    component: componentMap['/enterprise/checklist']!,
  },
  {
    label: 'Agent Run',
    path: '/agents/runs/:id',
    icon: navConfig.find(route => route.path === '/agents/runs')?.icon || LayoutDashboard,
    section: 'agents',
    status: 'active',
    description: 'Detalhes operacionais de uma execucao de agente.',
    hidden: true,
    component: componentMap['/agents/runs/:id']!,
  },
  {
    label: 'Workspace Artifacts',
    path: '/agents/workspaces/:id',
    icon: navConfig.find(route => route.path === '/agents/workspaces')?.icon || LayoutDashboard,
    section: 'agents',
    status: 'active',
    description: 'Artefatos de um workspace compartilhado.',
    hidden: true,
    component: componentMap['/agents/workspaces/:id']!,
  },
  {
    label: 'Artifact Detail',
    path: '/agents/workspaces/:id/artifacts/:artifactId',
    icon: navConfig.find(route => route.path === '/agents/workspaces')?.icon || LayoutDashboard,
    section: 'agents',
    status: 'active',
    description: 'Detalhes, diff e revisao de artefato.',
    hidden: true,
    component: componentMap['/agents/workspaces/:id/artifacts/:artifactId']!,
  },
])

/** Sidebar navigation structure helper */
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
    const arr = byGroup.get(r.section) || []
    arr.push(r)
    byGroup.set(r.section, arr)
  }

  const order = ['core', 'agents', 'operations', 'performance', 'enterprise', 'observability', 'compliance', 'advanced', 'developers']
  const groups: SidebarGroup[] = []
  for (const key of order) {
    const items = byGroup.get(key)
    if (!items || items.length === 0) continue
    const meta = sectionMeta[key] || { label: key, icon: LayoutDashboard }
    groups.push({ key, label: meta.label, icon: meta.icon, items })
  }
  return groups
}

/** Build breadcrumb trail from path */
export function buildBreadcrumbs(pathname: string): Array<{ label: string; path: string }> {
  if (pathname === '/') return []

  const crumbs: Array<{ label: string; path: string }> = []
  const segments = pathname.split('/').filter(Boolean)
  let acc = ''

  for (const seg of segments) {
    acc += '/' + seg
    const route = routes.find(r => r.path === acc)
    crumbs.push({
      label: route?.label || seg.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      path: acc,
    })
  }

  return crumbs
}
