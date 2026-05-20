import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Hub from './pages/Hub'
import Clients from './pages/Clients'
import Models from './pages/Models'
import Backends from './pages/Backends'
import Plugins from './pages/Plugins'
import ManagedControlPlane from './pages/ManagedControlPlane'
import OperationsOverview from './pages/operations/OperationsOverview'
import RuntimeNodes from './pages/operations/RuntimeNodes'
import ModelRuntime from './pages/operations/ModelRuntime'
import QueueQoS from './pages/operations/QueueQoS'
import Readiness from './pages/operations/Readiness'
import SecurityPosture from './pages/operations/SecurityPosture'
import ReleaseStatus from './pages/operations/ReleaseStatus'
import IncidentTimeline from './pages/operations/IncidentTimeline'
import PerformanceDashboard from './pages/performance/PerformanceDashboard'
import BenchmarkHistory from './pages/performance/BenchmarkHistory'
import TuningProfiles from './pages/performance/TuningProfiles'
import EnterpriseOnboardingDashboard from './pages/enterprise/EnterpriseOnboardingDashboard'
import OnboardingChecklist from './pages/enterprise/OnboardingChecklist'
import ObservabilityDashboard from './pages/observability/ObservabilityDashboard'
import MultiClusterOverview from './pages/multicluster/MultiClusterOverview'
import ChaosDashboard from './pages/chaos/ChaosDashboard'
import ComplianceOverview from './pages/compliance/ComplianceOverview'
import ControlMap from './pages/compliance/ControlMap'
import EvidenceCenter from './pages/compliance/EvidenceCenter'
import RiskRegister from './pages/compliance/RiskRegister'
import PolicyCenter from './pages/compliance/PolicyCenter'
import { useAuthStore } from './store/useAuthStore'
import { ShieldAlert, LogIn, Activity } from 'lucide-react'

const queryClient = new QueryClient()

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
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-3xl shadow-xl border border-slate-200 p-8">
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-teal-50 text-teal-600 rounded-2xl">
            <ShieldAlert className="w-8 h-8" />
          </div>
        </div>
        <h2 className="text-2xl font-bold text-slate-900 text-center mb-2">Acesso Administrativo</h2>
        <p className="text-slate-500 text-center mb-8">Informe seu X-Admin-Token para gerenciar a stack.</p>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Token de Admin</label>
            <input 
              type="password"
              placeholder="X-Admin-Token"
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition-all"
              value={value}
              onChange={(e) => setValue(e.target.value)}
            />
          </div>
          <button 
            onClick={handleConnect}
            className="w-full bg-slate-900 text-white font-bold py-3 rounded-xl hover:bg-slate-800 flex items-center justify-center gap-2 transition-colors"
          >
            <LogIn className="w-5 h-5" />
            Conectar ao Painel
          </button>
        </div>
      </div>
    </div>
  )
}

function Layout({ children }: { children: React.ReactNode }) {
  const logout = useAuthStore((state) => state.logout)
  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link to="/" className="font-black tracking-tighter text-xl">STACK<span className="text-teal-600">ADMIN</span></Link>
            <div className="hidden md:flex gap-6 text-sm font-bold text-slate-500">
              <Link to="/" className="hover:text-teal-600 transition-colors">Hub</Link>
              <Link to="/clients" className="hover:text-teal-600 transition-colors">Clientes</Link>
              <Link to="/models" className="hover:text-teal-600 transition-colors">Modelos</Link>
              <Link to="/backends" className="hover:text-teal-600 transition-colors">Backends</Link>
              <Link to="/plugins" className="hover:text-teal-600 transition-colors">Plugins</Link>
              <Link to="/operations" className="hover:text-teal-600 transition-colors flex items-center gap-1">
                <Activity className="w-3.5 h-3.5" />
                Operações
              </Link>
              <Link to="/saas" className="hover:text-teal-600 transition-colors">SaaS</Link>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1 bg-teal-50 text-teal-700 rounded-full">
              <div className="w-2 h-2 bg-teal-500 rounded-full animate-pulse"></div>
              <span className="text-[10px] font-black uppercase tracking-wider">Online</span>
            </div>
            <button 
              onClick={logout}
              className="text-sm font-bold text-slate-400 hover:text-red-500 transition-colors"
            >
              Sair
            </button>
          </div>
        </div>
      </nav>
      <main>
        {children}
      </main>
    </div>
  )
}

function App() {
  const token = useAuthStore((state) => state.token)

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/static/admin-v2">
        <Routes>
          <Route path="/login" element={token ? <Navigate to="/" replace /> : <Login />} />
          <Route 
            path="/" 
            element={
              <ProtectedRoute>
                <Layout><Hub /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/clients" 
            element={
              <ProtectedRoute>
                <Layout><Clients /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/models" 
            element={
              <ProtectedRoute>
                <Layout><Models /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/backends" 
            element={
              <ProtectedRoute>
                <Layout><Backends /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/plugins" 
            element={
              <ProtectedRoute>
                <Layout><Plugins /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/saas" 
            element={
              <ProtectedRoute>
                <Layout><ManagedControlPlane /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/operations" 
            element={
              <ProtectedRoute>
                <Layout><OperationsOverview /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/operations/nodes" 
            element={
              <ProtectedRoute>
                <Layout><RuntimeNodes /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/operations/runtime" 
            element={
              <ProtectedRoute>
                <Layout><ModelRuntime /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/operations/qos" 
            element={
              <ProtectedRoute>
                <Layout><QueueQoS /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/operations/readiness" 
            element={
              <ProtectedRoute>
                <Layout><Readiness /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/operations/security" 
            element={
              <ProtectedRoute>
                <Layout><SecurityPosture /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/operations/release" 
            element={
              <ProtectedRoute>
                <Layout><ReleaseStatus /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/operations/incidents" 
            element={
              <ProtectedRoute>
                <Layout><IncidentTimeline /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/performance" 
            element={
              <ProtectedRoute>
                <Layout><PerformanceDashboard /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/performance/history" 
            element={
              <ProtectedRoute>
                <Layout><BenchmarkHistory /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/performance/profiles" 
            element={
              <ProtectedRoute>
                <Layout><TuningProfiles /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/enterprise/onboarding" 
            element={
              <ProtectedRoute>
                <Layout><EnterpriseOnboardingDashboard /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/enterprise/onboarding/:id" 
            element={
              <ProtectedRoute>
                <Layout><OnboardingChecklist /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/observability" 
            element={
              <ProtectedRoute>
                <Layout><ObservabilityDashboard /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/multicluster" 
            element={
              <ProtectedRoute>
                <Layout><MultiClusterOverview /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/chaos" 
            element={
              <ProtectedRoute>
                <Layout><ChaosDashboard /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/compliance" 
            element={
              <ProtectedRoute>
                <Layout><ComplianceOverview /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/compliance/controls" 
            element={
              <ProtectedRoute>
                <Layout><ControlMap /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/compliance/evidence" 
            element={
              <ProtectedRoute>
                <Layout><EvidenceCenter /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/compliance/risks" 
            element={
              <ProtectedRoute>
                <Layout><RiskRegister /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/compliance/policies" 
            element={
              <ProtectedRoute>
                <Layout><PolicyCenter /></Layout>
              </ProtectedRoute>
            } 
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
