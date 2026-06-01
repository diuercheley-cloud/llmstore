import { useState, Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from './store/useAuthStore'
import { ShieldAlert, LogIn, Loader2 } from 'lucide-react'
import { ThemeProvider } from './components/theme-provider'
import { AdminShell } from './components/layout/AdminShell'
import { CommandPalette } from './components/command-palette'
import { OnboardingWizard } from './components/onboarding-wizard'
import { Toaster } from 'sonner'
import { NotFound } from './components/ui-feedback'
import { routes, type RouteConfig } from './routes/adminRoutes'
import { FeatureGate } from './components/layout/FeatureGate'

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

function RouteRenderer({ route }: { route: RouteConfig }) {
  // Check if route is coming soon or disabled
  if (route.status === 'coming_soon' || route.status === 'disabled') {
     return <FeatureGate feature={route.label} />
  }

  return <route.component />
}

function Login() {
  const [value, setValue] = useState('')
  const [ssoLoading, setSsoLoading] = useState<string | null>(null)
  const setToken = useAuthStore(state => state.setToken)

  // Capture SSO token from URL on mount
  useState(() => {
    const hashParams = new URLSearchParams(window.location.hash.split('?')[1] || '')
    const searchParams = new URLSearchParams(window.location.search)
    const params = hashParams.get('sso_token') ? hashParams : searchParams
    const ssoToken = params.get('sso_token')
    if (ssoToken) {
      setToken(ssoToken)
      window.history.replaceState({}, '', '/admin-dashboard')
    }
  })

  const handleSSOLogin = async (provider: string) => {
    setSsoLoading(provider)
    try {
      const resp = await fetch(`/auth/login/${provider}`)
      if (!resp.ok) {
        const err = await resp.json()
        alert(err.detail || 'SSO login unavailable')
        return
      }
      const data = await resp.json()
      window.location.href = data.url
    } catch {
      alert('SSO login failed')
    } finally {
      setSsoLoading(null)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <main className="max-w-md w-full bg-card rounded-3xl shadow-xl border border-border p-8">
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-primary/10 text-primary rounded-2xl">
            <ShieldAlert className="w-8 h-8" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-foreground text-center mb-2">Acesso Administrativo</h1>
        <p className="text-muted-foreground text-center mb-8">Entre com sua conta ou token de administrador.</p>
        <div className="space-y-3 mb-6">
          <button
            onClick={() => handleSSOLogin('google')}
            disabled={ssoLoading !== null}
            className="w-full bg-white text-gray-800 font-medium py-3 rounded-xl border border-border hover:bg-gray-50 flex items-center justify-center gap-3 transition-all disabled:opacity-50"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            {ssoLoading === 'google' ? 'Conectando...' : 'Continuar com Google'}
          </button>
          <button
            onClick={() => handleSSOLogin('github')}
            disabled={ssoLoading !== null}
            className="w-full bg-gray-900 text-white font-medium py-3 rounded-xl hover:bg-gray-800 flex items-center justify-center gap-3 transition-all disabled:opacity-50"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
            {ssoLoading === 'github' ? 'Conectando...' : 'Continuar com GitHub'}
          </button>
        </div>
        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-border" /></div>
          <div className="relative flex justify-center text-xs uppercase"><span className="bg-card px-2 text-muted-foreground">Ou token de admin</span></div>
        </div>
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

// ── App ───────────────────────────────────────────────────────────

const queryClient = new QueryClient()

function App() {
  const token = useAuthStore(state => state.token)

  return (
    <ThemeProvider defaultTheme="system" storageKey="admin-theme">
      <QueryClientProvider client={queryClient}>
        <Toaster position="top-right" expand={false} richColors closeButton />
        <BrowserRouter basename="/admin-dashboard">
          <CommandPalette />
          <OnboardingWizard />
          <Routes>
            {/* Login */}
            <Route path="/login" element={token ? <Navigate to="/" replace /> : <Login />} />

            {/* Centralized routes from adminRoutes.tsx */}
            {routes.map(route => (
              <Route
                key={route.path}
                path={route.path}
                element={
                  <ProtectedRoute>
                    <AdminShell layout={route.layout}>
                      <Suspense fallback={<PageLoader />}>
                        <RouteRenderer route={route} />
                      </Suspense>
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
