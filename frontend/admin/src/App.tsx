import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Hub from './pages/Hub'
import Clients from './pages/Clients'
import Models from './pages/Models'
import Backends from './pages/Backends'
import { useAuthStore } from './store/useAuthStore'
import { ShieldAlert, LogIn } from 'lucide-react'

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
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
