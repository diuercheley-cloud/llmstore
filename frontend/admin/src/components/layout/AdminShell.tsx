import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { X, Menu, HelpCircle, RotateCcw, LogOut } from 'lucide-react'
import { useAuthStore } from '../../store/useAuthStore'
import { ThemeToggle } from '../theme-toggle'
import { Sidebar } from './Sidebar'
import { Breadcrumbs } from './Breadcrumbs'
import api from '../../lib/api'

interface AdminShellProps {
  children: React.ReactNode
  layout?: 'default' | 'minimal' | 'full'
}

export function AdminShell({ children, layout = 'default' }: AdminShellProps) {
  const logout = useAuthStore(state => state.logout)
  const [showHelp, setShowHelp] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const restartOnboarding = async () => {
    try {
      await api.post('/admin/onboarding/status', { is_finished: false })
      window.location.reload()
    } catch (e) {
      console.error(e)
    }
  }

  if (layout === 'full') {
    return <div className="h-screen w-screen overflow-hidden">{children}</div>
  }

  return (
    <div className="min-h-screen bg-background font-sans text-foreground flex">
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 bg-card border-r border-border
        flex flex-col
        transform transition-transform duration-300 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Logo */}
        <div className="flex items-center justify-between mb-4 px-4 py-4 border-b border-border">
          <Link to="/" className="font-black tracking-tighter text-xl" onClick={() => setSidebarOpen(false)}>
            STACK<span className="text-primary">ADMIN</span>
          </Link>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden p-1.5 hover:bg-secondary rounded-lg">
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <Sidebar onNavigate={() => setSidebarOpen(false)} />

        {/* Footer */}
        <div className="p-3 border-t border-border">
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-all"
          >
            <LogOut size={16} />
            <span>Sair</span>
          </button>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Sticky header */}
        <header className="bg-card border-b border-border sticky top-0 z-30">
          <nav className="px-4 h-14 flex items-center justify-between" aria-label="Top navigation">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 lg:hidden hover:bg-secondary rounded-lg transition-colors"
                aria-label="Open menu"
              >
                <Menu size={18} />
              </button>
              <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 bg-primary/10 text-primary rounded-full" role="status">
                <div className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse" />
                <span className="text-[10px] font-bold uppercase tracking-wider">Online</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative">
                <button
                  onClick={() => setShowHelp(!showHelp)}
                  className="p-2 hover:bg-secondary rounded-lg text-muted-foreground transition-colors"
                  aria-label="Help"
                >
                  <HelpCircle size={18} />
                </button>
                {showHelp && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setShowHelp(false)} />
                    <div className="absolute right-0 mt-2 w-48 bg-card border border-border rounded-xl shadow-xl z-50 overflow-hidden">
                      <button
                        onClick={restartOnboarding}
                        className="w-full flex items-center gap-2 px-4 py-2.5 text-sm font-medium hover:bg-secondary transition-colors"
                      >
                        <RotateCcw size={14} />
                        Reiniciar Onboarding
                      </button>
                      <a
                        href="https://docs.inference-stack.com"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="w-full flex items-center gap-2 px-4 py-2.5 text-sm font-medium hover:bg-secondary border-t border-border transition-colors"
                      >
                        <HelpCircle size={14} />
                        Documentacao
                      </a>
                    </div>
                  </>
                )}
              </div>
              <ThemeToggle />
            </div>
          </nav>
        </header>

        {/* Page content */}
        <main id="main-content" tabIndex={-1} className="flex-1 p-4 md:p-8 outline-none overflow-x-hidden">
          <div className="max-w-7xl mx-auto">
            <Breadcrumbs />
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
