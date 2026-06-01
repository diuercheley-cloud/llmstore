import { lazy } from 'react'
import { navConfig, type NavRoute, sectionMeta, type RouteStatus } from '../navigation/navConfig'
import type { LucideIcon } from 'lucide-react'
import { LayoutDashboard } from 'lucide-react'

// ── Lazy Component Map ────────────────────────────────────────────

const componentMap: Record<string, React.LazyExoticComponent<React.ComponentType<any>>> = {
  '/': lazy(() => import('../pages/operations/OperationsOverview')),
  '/clients': lazy(() => import('../pages/Clients')),
  '/models': lazy(() => import('../pages/Models')),
  '/backends': lazy(() => import('../pages/Backends')),
  '/plugins': lazy(() => import('../pages/Plugins')),
  '/saas': lazy(() => import('../pages/ManagedControlPlane')),
  '/api-keys': lazy(() => import('../pages/api-keys/ApiKeys')),
  '/rbac': lazy(() => import('../pages/rbac/RbacManagement')),
  '/billing': lazy(() => import('../pages/billing/Billing')),
  '/billing/reconciliation': lazy(() => import('../pages/billing/Reconciliation')),
  '/billing/disputes': lazy(() => import('../pages/billing/Disputes')),
  '/usage': lazy(() => import('../pages/usage/Usage')),
  '/rag': lazy(() => import('../pages/rag/Rag')),
  '/security': lazy(() => import('../pages/security/Security')),
  '/reports': lazy(() => import('../pages/reports/Reports')),
  '/settings': lazy(() => import('../pages/settings/Settings')),

  '/modules': lazy(() => import('../pages/Hub')),
  '/compliance': lazy(() => import('../pages/compliance/ComplianceOverview')),
  '/security/abuse': lazy(() => import('../pages/security/AbuseMonitoring')),
  '/compliance/controls': lazy(() => import('../pages/compliance/ControlMap')),
  '/compliance/risks': lazy(() => import('../pages/compliance/RiskRegister')),
  '/compliance/policies': lazy(() => import('../pages/compliance/PolicyCenter')),
  '/compliance/evidence': lazy(() => import('../pages/compliance/EvidenceCenter')),
  
  '/observability': lazy(() => import('../pages/observability/ObservabilityDashboard')),
  '/observability/agents': lazy(() => import('../pages/observability/AgentObservability')),
  '/performance': lazy(() => import('../pages/performance/PerformanceDashboard')),
  '/performance/history': lazy(() => import('../pages/performance/BenchmarkHistory')),
  '/performance/profiles': lazy(() => import('../pages/performance/TuningProfiles')),
  '/enterprise/onboarding': lazy(() => import('../pages/enterprise/EnterpriseOnboardingDashboard')),
  '/enterprise/checklist': lazy(() => import('../pages/enterprise/OnboardingChecklist')),
  '/enterprise/checklist/:id': lazy(() => import('../pages/enterprise/OnboardingChecklist')),

  '/agents': lazy(() => import('../pages/agents/AgentsOverview')),
  '/agents/studio': lazy(() => import('../pages/agents/studio/AgentStudio')),
  '/agents/analytics': lazy(() => import('../pages/agents/analytics/AgentAnalyticsDashboard')),
  '/agents/approvals': lazy(() => import('../pages/agents/approvals/ApprovalPortal')),
  '/agents/chat': lazy(() => import('../pages/chat/CollaborativeChat')),
  '/agents/promotion': lazy(() => import('../pages/agents/AgentPromotion')),
  '/agents/lineage': lazy(() => import('../pages/agents/AgentLineage')),
  '/agents/mcp': lazy(() => import('../pages/agents/mcp/MCPDashboard')),
  '/agents/deployments': lazy(() => import('../pages/agents/deployments/DeploymentsOverview')),
  '/agents/kg': lazy(() => import('../pages/agents/kg/KnowledgeGraph')),
  '/agents/optimization': lazy(() => import('../pages/agents/optimization/OptimizationTournaments')),

  '/operations/gpu': lazy(() => import('../pages/operations/GPUAutoscaling')),
  '/operations/adapters': lazy(() => import('../pages/operations/AdapterRegistry')),

  '/ide': lazy(() => import('../pages/ide/WebIDE')),
  '/developers': lazy(() => import('../pages/developers/DeveloperPortal')),
  '/developers/bundles': lazy(() => import('../pages/developers/Bundles')),
  '/prompts': lazy(() => import('../pages/prompts/Prompts')),

  '/multicluster': lazy(() => import('../pages/multicluster/MultiClusterOverview')),
  '/advanced/federation': lazy(() => import('../pages/advanced/FederationOverview')),
  '/chaos': lazy(() => import('../pages/chaos/ChaosDashboard')),
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
