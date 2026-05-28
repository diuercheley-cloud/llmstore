import { useState, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from './store/useAuthStore'
import { 
  ShieldAlert, 
  LogIn, 
  Activity, 
  HelpCircle, 
  RotateCcw, 
  Menu, 
  X, 
  LayoutDashboard, 
  Users, 
  Box, 
  Server, 
  Zap, 
  Cloud,
  LogOut,
  Loader2,
  CheckSquare,
  Bot
} from 'lucide-react'
import { ThemeProvider } from './components/theme-provider'
import { ThemeToggle } from './components/theme-toggle'
import { CommandPalette } from './components/command-palette'
import { OnboardingWizard } from './components/onboarding-wizard'
import { Toaster } from 'sonner'
import { NotFound } from './components/ui-feedback'
import api from './lib/api'

// Lazy loaded components
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
const MultiClusterOverview = lazy(() => import('./pages/multicluster/MultiClusterOverview'))
const ChaosDashboard = lazy(() => import('./pages/chaos/ChaosDashboard'))
const ComplianceOverview = lazy(() => import('./pages/compliance/ComplianceOverview'))
const ControlMap = lazy(() => import('./pages/compliance/ControlMap'))
const EvidenceCenter = lazy(() => import('./pages/compliance/EvidenceCenter'))
const RiskRegister = lazy(() => import('./pages/compliance/RiskRegister'))
const PolicyCenter = lazy(() => import('./pages/compliance/PolicyCenter'))
const RealtimeDashboard = lazy(() => import('./pages/observability/RealtimeDashboard'))
const AgentObservability = lazy(() => import('./pages/observability/AgentObservability'))

// Agent Pages
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

const queryClient = new QueryClient()

function PageLoader() {
  return (
    <div className="h-[60vh] flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
        <p className="text-sm font-bold text-muted-foreground animate-pulse">Carregando módulo...</p>
      </div>
    </div>
  )
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((state) => state.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function Login() {
  const [value, setValue] = useState('')
  const setToken = useAuthStore((state) => state.setToken)

  const handleConnect = () => {
    if (value.trim()) {
      setToken(value.trim())
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <main className="max-w-md w-full bg-card rounded-3xl shadow-xl border border-border p-8" aria-labelledby="login-title">
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-primary/10 text-primary rounded-2xl" role="presentation">
            <ShieldAlert className="w-8 h-8" aria-hidden="true" />
          </div>
        </div>
        <h1 id="login-title" className="text-2xl font-bold text-foreground text-center mb-2">Acesso Administrativo</h1>
        <p className="text-muted-foreground text-center mb-8">Informe seu X-Admin-Token para gerenciar a stack.</p>
        
        <form 
          className="space-y-4" 
          onSubmit={(e) => { e.preventDefault(); handleConnect(); }}
        >
          <div>
            <label htmlFor="admin-token" className="block text-sm font-semibold text-foreground mb-2">Token de Admin</label>
            <input 
              id="admin-token"
              type="password"
              placeholder="X-Admin-Token"
              className="w-full px-4 py-3 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              required
              aria-required="true"
            />
          </div>
          <button 
            type="submit"
            className="w-full bg-foreground text-background font-bold py-3 rounded-xl hover:opacity-90 flex items-center justify-center gap-2 transition-all focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
          >
            <LogIn className="w-5 h-5" aria-hidden="true" />
            Conectar ao Painel
          </button>
        </form>
      </main>
    </div>
  )
}

function Layout({ children }: { children: React.ReactNode }) {
  const logout = useAuthStore((state) => state.logout)
  const [showHelp, setShowHelp] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const location = useLocation()

  const restartOnboarding = async () => {
    try {
      await api.post("/admin/onboarding/status", { is_finished: false })
      window.location.reload()
    } catch (e) {
      console.error(e)
    }
  }

  const navItems = [
    { to: "/", label: "Hub", icon: LayoutDashboard },
    { to: "/clients", label: "Clientes", icon: Users },
    { to: "/models", label: "Modelos", icon: Box },
    { to: "/backends", label: "Backends", icon: Server },
    { to: "/plugins", label: "Plugins", icon: Zap },
    { to: "/operations", label: "Operações", icon: Activity },
    { to: "/saas", label: "SaaS", icon: Cloud },
    { to: "/agents", label: "Agentes", icon: Bot },
  ]

  return (
    <div className="min-h-screen bg-background font-sans text-foreground flex">
      {/* Mobile Backdrop */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden transition-opacity"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 bg-card border-r border-border p-4
        transform transition-transform duration-300 ease-in-out
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        flex flex-col
      `}>
        <div className="flex items-center justify-between mb-8 px-2">
          <Link to="/" className="font-black tracking-tighter text-xl">
            STACK<span className="text-primary">ADMIN</span>
          </Link>
          <button onClick={() => setIsSidebarOpen(false)} className="lg:hidden p-2 hover:bg-secondary rounded-lg">
            <X size={20} />
          </button>
        </div>
        
        <nav className="flex-1 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.to || (item.to !== "/" && location.pathname.startsWith(item.to))
            return (
              <Link
                key={item.to}
                to={item.to}
                onClick={() => setIsSidebarOpen(false)}
                className={`
                  flex items-center gap-3 px-4 py-2.5 rounded-xl font-bold transition-all
                  ${isActive 
                    ? 'bg-primary/10 text-primary shadow-sm' 
                    : 'text-muted-foreground hover:bg-secondary hover:text-foreground'}
                `}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>

        <div className="pt-4 mt-4 border-t border-border space-y-2">
          <button 
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl font-bold text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-all"
          >
            <LogOut size={18} />
            <span>Sair</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-card border-b border-border sticky top-0 z-30">
          <nav className="px-4 h-16 flex items-center justify-between" aria-label="Navegação superior">
            <div className="flex items-center gap-4">
              <button 
                onClick={() => setIsSidebarOpen(true)}
                className="p-2 lg:hidden hover:bg-secondary rounded-lg transition-colors"
                aria-label="Abrir menu"
              >
                <Menu size={20} />
              </button>
              <div className="hidden lg:flex items-center gap-2 px-3 py-1 bg-primary/10 text-primary rounded-full" role="status" aria-label="Sistema online">
                <div className="w-2 h-2 bg-primary rounded-full animate-pulse" aria-hidden="true"></div>
                <span className="text-[10px] font-black uppercase tracking-wider">Online</span>
              </div>
            </div>

            <div className="flex items-center gap-2 md:gap-4">
              <div className="relative">
                <button 
                  onClick={() => setShowHelp(!showHelp)}
                  className="p-2 hover:bg-secondary rounded-lg text-muted-foreground transition-colors focus-visible:ring-2 focus-visible:ring-primary outline-none"
                  aria-label="Menu de ajuda"
                  aria-expanded={showHelp}
                >
                  <HelpCircle className="w-5 h-5" aria-hidden="true" />
                </button>
                {showHelp && (
                  <div className="absolute right-0 mt-2 w-48 bg-card border border-border rounded-xl shadow-xl z-[60] overflow-hidden animate-in fade-in slide-in-from-top-2">
                    <button 
                      onClick={restartOnboarding}
                      className="w-full flex items-center gap-2 px-4 py-3 text-sm font-semibold hover:bg-secondary transition-colors"
                    >
                      <RotateCcw className="w-4 h-4" aria-hidden="true" />
                      Reiniciar Onboarding
                    </button>
                    <a 
                      href="https://docs.inference-stack.com" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="w-full flex items-center gap-2 px-4 py-3 text-sm font-semibold hover:bg-secondary border-t border-border transition-colors"
                    >
                      <HelpCircle className="w-4 h-4" aria-hidden="true" />
                      Documentação
                    </a>
                  </div>
                )}
              </div>
              <ThemeToggle />
            </div>
          </nav>
        </header>
        
        <main id="main-content" tabIndex={-1} className="flex-1 p-4 md:p-8 outline-none overflow-x-hidden">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

function App() {
  const token = useAuthStore((state) => state.token)

  return (
    <ThemeProvider defaultTheme="system" storageKey="admin-theme">
      <QueryClientProvider client={queryClient}>
        <Toaster position="top-right" expand={false} richColors closeButton />
        <BrowserRouter basename="/static/admin-v2">
          <CommandPalette />
          <OnboardingWizard />
          <Routes>
            <Route path="/login" element={token ? <Navigate to="/" replace /> : <Login />} />
            <Route 
              path="/" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><Hub /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/clients" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><Clients /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/models" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><Models /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/backends" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><Backends /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/plugins" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><Plugins /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/saas" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><ManagedControlPlane /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/operations" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><OperationsOverview /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/operations/nodes" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><RuntimeNodes /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/operations/runtime" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><ModelRuntime /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/operations/qos" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><QueueQoS /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/operations/readiness" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><Readiness /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/operations/security" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><SecurityPosture /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/operations/release" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><ReleaseStatus /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/operations/incidents" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><IncidentTimeline /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/performance" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><PerformanceDashboard /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/performance/history" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><BenchmarkHistory /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/performance/profiles" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><TuningProfiles /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/enterprise/onboarding" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><EnterpriseOnboardingDashboard /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/enterprise/onboarding/:id" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><OnboardingChecklist /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/observability" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><ObservabilityDashboard /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/observability/realtime" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><RealtimeDashboard /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/observability/agents" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><AgentObservability /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/multicluster" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><MultiClusterOverview /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/chaos" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><ChaosDashboard /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/compliance" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><ComplianceOverview /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/compliance/controls" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><ControlMap /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/compliance/evidence" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><EvidenceCenter /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/compliance/risks" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><RiskRegister /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/compliance/policies" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><PolicyCenter /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/agent-approvals" 
              element={
                <ProtectedRoute>
                  <Layout><Suspense fallback={<PageLoader />}><AgentApprovals /></Suspense></Layout>
                </ProtectedRoute>
              } 
            />
            {/* Agent Control Plane Routes */}
            <Route path="/agents" element={<ProtectedRoute><Layout><Suspense fallback={<PageLoader />}><AgentsOverview /></Suspense></Layout></ProtectedRoute>} />
            <Route path="/agents/registry" element={<ProtectedRoute><Layout><Suspense fallback={<PageLoader />}><AgentRegistry /></Suspense></Layout></ProtectedRoute>} />
            <Route path="/agents/runs" element={<ProtectedRoute><Layout><Suspense fallback={<PageLoader />}><AgentRuns /></Suspense></Layout></ProtectedRoute>} />
            <Route path="/agents/runs/:id" element={<ProtectedRoute><Layout><Suspense fallback={<PageLoader />}><AgentRunTimeline /></Suspense></Layout></ProtectedRoute>} />
            <Route path="/agents/tools" element={<ProtectedRoute><Layout><Suspense fallback={<PageLoader />}><AgentTools /></Suspense></Layout></ProtectedRoute>} />
            <Route path="/agents/memory" element={<ProtectedRoute><Layout><Suspense fallback={<PageLoader />}><AgentMemory /></Suspense></Layout></ProtectedRoute>} />
            <Route path="/agents/approvals" element={<ProtectedRoute><Layout><Suspense fallback={<PageLoader />}><AgentApprovals /></Suspense></Layout></ProtectedRoute>} />
            <Route path="/agents/evals" element={<ProtectedRoute><Layout><Suspense fallback={<PageLoader />}><AgentEvals /></Suspense></Layout></ProtectedRoute>} />
            <Route path="/agents/policies" element={<ProtectedRoute><Layout><Suspense fallback={<PageLoader />}><AgentPolicies /></Suspense></Layout></ProtectedRoute>} />
            <Route path="/agents/marketplace" element={<ProtectedRoute><Layout><Suspense fallback={<PageLoader />}><AgentMarketplace /></Suspense></Layout></ProtectedRoute>} />
            <Route path="/agents/workspaces" element={<ProtectedRoute><Layout><Suspense fallback={<PageLoader />}><AgentWorkspaces /></Suspense></Layout></ProtectedRoute>} />
            <Route path="/agents/workspaces/:id" element={<ProtectedRoute><Layout><Suspense fallback={<PageLoader />}><AgentArtifactBrowser /></Suspense></Layout></ProtectedRoute>} />
            <Route path="/agents/workspaces/:id/artifacts/:artifactId" element={<ProtectedRoute><Layout><Suspense fallback={<PageLoader />}><AgentArtifactDetail /></Suspense></Layout></ProtectedRoute>} />

            <Route path="*" element={<Layout><NotFound /></Layout>} />

          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
