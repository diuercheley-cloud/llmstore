import { useState, Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from './store/useAuthStore'
import { ShieldAlert, LogIn, Loader2 } from 'lucide-react'
import { ThemeProvider } from './components/theme-provider'
import { AdminShell } from './components/layout/AdminShell'
import { FeatureGate } from './components/layout/FeatureGate'
import { CommandPalette } from './components/command-palette'
import { OnboardingWizard } from './components/onboarding-wizard'
import { Toaster } from 'sonner'
import { NotFound } from './components/ui-feedback'
import { navRoutes, type NavRoute } from './navigation/navConfig'

// ── Lazy page imports (generated from navRoutes) ──────────────────

const Hub = lazy(() => import('./pages/Hub'))
const Clients = lazy(() => import('./pages/Clients'))
const Models = lazy(() => import('./pages/Models'))
const Backends = lazy(() => import('./pages/Backends'))
const Plugins = lazy(() => import('./pages/Plugins'))
const ManagedControlPlane = lazy(() => import('./pages/ManagedControlPlane'))
const OperationsOverview = lazy(() => import('./pages/operations/OperationsOverview'))
const RuntimeNodes = lazy(() => import('./pages/operations/RuntimeNodes'))
const ModelRuntime = lazy(() => import('./pages/operations/ModelRuntime'))
const QueueQoS = lazy(() => import('./pages/operations/QueueQoS'))
const Readiness = lazy(() => import('./pages/operations/Readiness'))
const SecurityPosture = lazy(() => import('./pages/operations/SecurityPosture'))
const ReleaseStatus = lazy(() => import('./pages/operations/ReleaseStatus'))
const IncidentTimeline = lazy(() => import('./pages/operations/IncidentTimeline'))
const PerformanceDashboard = lazy(() => import('./pages/performance/PerformanceDashboard'))
const BenchmarkHistory = lazy(() => import('./pages/performance/BenchmarkHistory'))
const TuningProfiles = lazy(() => import('./pages/performance/TuningProfiles'))
const EnterpriseOnboardingDashboard = lazy(() => import('./pages/enterprise/EnterpriseOnboardingDashboard'))
const OnboardingChecklist = lazy(() => import('./pages/enterprise/OnboardingChecklist'))
const ObservabilityDashboard = lazy(() => import('./pages/observability/ObservabilityDashboard'))
const RealtimeDashboard = lazy(() => import('./pages/observability/RealtimeDashboard'))
const AgentObservability = lazy(() => import('./pages/observability/AgentObservability'))
const MultiClusterOverview = lazy(() => import('./pages/multicluster/MultiClusterOverview'))
const ChaosDashboard = lazy(() => import('./pages/chaos/ChaosDashboard'))
const ComplianceOverview = lazy(() => import('./pages/compliance/ComplianceOverview'))
const ControlMap = lazy(() => import('./pages/compliance/ControlMap'))
const EvidenceCenter = lazy(() => import('./pages/compliance/EvidenceCenter'))
const RiskRegister = lazy(() => import('./pages/compliance/RiskRegister'))
const PolicyCenter = lazy(() => import('./pages/compliance/PolicyCenter'))
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
const AgentStudio = lazy(() => import('./pages/agents/studio/AgentStudio'))
const AgentAnalyticsDashboard = lazy(() => import('./pages/agents/analytics/AgentAnalyticsDashboard'))
const ApprovalPortal = lazy(() => import('./pages/agents/approvals/ApprovalPortal'))
const AgentPromotion = lazy(() => import('./pages/agents/AgentPromotion'))
const AgentLineage = lazy(() => import('./pages/agents/AgentLineage'))
const CollaborativeChat = lazy(() => import('./pages/chat/CollaborativeChat'))
const WebIDE = lazy(() => import('./pages/ide/WebIDE'))
const DeveloperPortal = lazy(() => import('./pages/developers/DeveloperPortal'))
const Bundles = lazy(() => import('./pages/developers/Bundles'))

// ── Component map (path -> lazy component) ────────────────────────

const componentMap: Record<string, React.LazyExoticComponent<React.FC<Record<string, unknown>>>> = {
  '/': Hub,
  '/clients': Clients,
  '/models': Models,
  '/backends': Backends,
  '/plugins': Plugins,
  '/saas': ManagedControlPlane,
  '/operations': OperationsOverview,
  '/operations/nodes': RuntimeNodes,
  '/operations/runtime': ModelRuntime,
  '/operations/qos': QueueQoS,
  '/operations/readiness': Readiness,
  '/operations/security': SecurityPosture,
  '/operations/release': ReleaseStatus,
  '/operations/incidents': IncidentTimeline,
  '/performance': PerformanceDashboard,
  '/performance/history': BenchmarkHistory,
  '/performance/profiles': TuningProfiles,
  '/enterprise/onboarding': EnterpriseOnboardingDashboard,
  '/enterprise/onboarding/:id': OnboardingChecklist,
  '/observability': ObservabilityDashboard,
  '/observability/realtime': RealtimeDashboard,
  '/observability/agents': AgentObservability,
  '/multicluster': MultiClusterOverview,
  '/chaos': ChaosDashboard,
  '/compliance': ComplianceOverview,
  '/compliance/controls': ControlMap,
  '/compliance/evidence': EvidenceCenter,
  '/compliance/risks': RiskRegister,
  '/compliance/policies': PolicyCenter,
  '/agents': AgentsOverview,
  '/agents/registry': AgentRegistry,
  '/agents/runs': AgentRuns,
  '/agents/runs/:id': AgentRunTimeline,
  '/agents/tools': AgentTools,
  '/agents/memory': AgentMemory,
  '/agents/approvals': AgentApprovals,
  '/agents/evals': AgentEvals,
  '/agents/policies': AgentPolicies,
  '/agents/marketplace': AgentMarketplace,
  '/agents/workspaces': AgentWorkspaces,
  '/agents/workspaces/:id': AgentArtifactBrowser,
  '/agents/workspaces/:id/artifacts/:artifactId': AgentArtifactDetail,
  '/agents/studio': AgentStudio,
  '/agents/analytics': AgentAnalyticsDashboard,
  '/agents/approvals-portal': ApprovalPortal,
  '/agents/promotion': AgentPromotion,
  '/agents/lineage': AgentLineage,
  '/agents/chat': CollaborativeChat,
  '/ide': WebIDE,
  '/developers': DeveloperPortal,
  '/developers/bundles': Bundles,
}

// ── Shared components ─────────────────────────────────────────────

function PageLoader() {
  return (
    <div className="h-[60vh] flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
        <p className="text-sm font-medium text-muted-foreground animate-pulse">Carregando modulo...</p>
      </div>
    </div>
  )
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore(state => state.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function Login() {
  const [value, setValue] = useState('')
  const setToken = useAuthStore(state => state.setToken)

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <main className="max-w-md w-full bg-card rounded-3xl shadow-xl border border-border p-8">
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-primary/10 text-primary rounded-2xl">
            <ShieldAlert className="w-8 h-8" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-foreground text-center mb-2">Acesso Administrativo</h1>
        <p className="text-muted-foreground text-center mb-8">Informe seu X-Admin-Token para gerenciar a stack.</p>
        <form className="space-y-4" onSubmit={e => { e.preventDefault(); if (value.trim()) setToken(value.trim()) }}>
          <div>
            <label htmlFor="admin-token" className="block text-sm font-semibold text-foreground mb-2">Token de Admin</label>
            <input
              id="admin-token"
              type="password"
              placeholder="X-Admin-Token"
              className="w-full px-4 py-3 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all"
              value={value}
              onChange={e => setValue(e.target.value)}
              required
            />
          </div>
          <button
            type="submit"
            className="w-full bg-foreground text-background font-bold py-3 rounded-xl hover:opacity-90 flex items-center justify-center gap-2 transition-all"
          >
            <LogIn className="w-5 h-5" />
            Conectar ao Painel
          </button>
        </form>
      </main>
    </div>
  )
}

function ComingSoonInline({ title, description }: { title: string; description?: string }) {
  return (
    <FeatureGate
      feature={title}
      message={description || `${title} esta em desenvolvimento e estara disponivel em breve.`}
    />
  )
}

// ── Placeholder routes for pages not yet built ────────────────────

const placeholderRoutes = [
  { path: '/api-keys', label: 'API Keys', description: 'Emissao, rotacao e governanca de credenciais.' },
  { path: '/billing', label: 'Billing', description: 'Planos, pricing e cobranca.' },
  { path: '/usage', label: 'Uso', description: 'Consumo por cliente e metricas agregadas.' },
  { path: '/rag', label: 'RAG', description: 'Vaults e documentos da camada RAG.' },
  { path: '/security', label: 'Seguranca', description: 'Auditoria e eventos de seguranca.' },
  { path: '/reports', label: 'Relatorios', description: 'Relatorios executivos e exportacoes.' },
  { path: '/settings', label: 'Configuracoes', description: 'Configuracao geral do sistema.' },
]

// ── App ───────────────────────────────────────────────────────────

const queryClient = new QueryClient()

function App() {
  const token = useAuthStore(state => state.token)

  return (
    <ThemeProvider defaultTheme="system" storageKey="admin-theme">
      <QueryClientProvider client={queryClient}>
        <Toaster position="top-right" expand={false} richColors closeButton />
        <BrowserRouter basename="/static/admin-v2">
          <CommandPalette />
          <OnboardingWizard />
          <Routes>
            {/* Login */}
            <Route path="/login" element={token ? <Navigate to="/" replace /> : <Login />} />

            {/* Real routes from navRoutes */}
            {navRoutes
              .filter(r => componentMap[r.path])
              .map(route => (
                <Route
                  key={route.path}
                  path={route.path}
                  element={
                    <ProtectedRoute>
                      <AdminShell>
                        <Suspense fallback={<PageLoader />}>
                          {(() => {
                            const Comp = componentMap[route.path]
                            return Comp ? <Comp /> : <FeatureGate feature={route.label} />
                          })()}
                        </Suspense>
                      </AdminShell>
                    </ProtectedRoute>
                  }
                />
              ))}

            {/* Placeholder routes */}
            {placeholderRoutes.map(pr => (
              <Route
                key={pr.path}
                path={pr.path}
                element={
                  <ProtectedRoute>
                    <AdminShell>
                      <ComingSoonInline title={pr.label} description={pr.description} />
                    </AdminShell>
                  </ProtectedRoute>
                }
              />
            ))}

            {/* 404 */}
            <Route path="*" element={<AdminShell><NotFound /></AdminShell>} />
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
