import { useTheme } from '../../components/theme-provider'
import { useLocation, Link } from 'react-router-dom'
import {
  ChevronRight,
  LayoutDashboard,
  Bot,
  Activity,
  TrendingUp,
  Briefcase,
  Monitor,
  Gavel,
  Network,
  Code2,
  ChevronDown,
} from 'lucide-react'
import { navSections, getSectionRoutes, type NavSection, type NavRoute } from '../../navigation/navConfig'
import { isRouteDisabled } from '../../navigation/navConfig'
import type { ReactNode } from 'react'

interface SidebarProps {
  collapsed?: boolean
  onNavigate?: () => void
}

const sectionIconMap: Record<string, ReactNode> = {
  core: <LayoutDashboard size={16} />,
  agents: <Bot size={16} />,
  operations: <Activity size={16} />,
  performance: <TrendingUp size={16} />,
  enterprise: <Briefcase size={16} />,
  observability: <Monitor size={16} />,
  compliance: <Gavel size={16} />,
  advanced: <Network size={16} />,
  developers: <Code2 size={16} />,
}

function SidebarSection({ section, onNavigate }: { section: NavSection; onNavigate?: () => void }) {
  const location = useLocation()
  const routes = getSectionRoutes(section.key)

  if (routes.length === 0) return null

  const isActive = routes.some(r => location.pathname === r.path || (r.path !== '/' && location.pathname.startsWith(r.path)))

  // Single route -> flat link
  if (routes.length === 1) {
    const route = routes[0]
    const Icon = route.icon
    const disabled = isRouteDisabled(route.status)
    return (
      <Link
        to={disabled ? '#' : route.path}
        onClick={e => { if (disabled) e.preventDefault(); onNavigate?.() }}
        className={`
          flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all
          ${isActive ? 'bg-primary/10 text-primary' : disabled ? 'text-muted-foreground/50 cursor-not-allowed' : 'text-muted-foreground hover:bg-secondary hover:text-foreground'}
        `}
      >
        <Icon size={16} />
        <span className="flex-1">{route.label}</span>
        {route.status === 'coming_soon' && (
          <span className="text-[8px] font-bold uppercase px-1.5 py-0.5 bg-muted rounded text-muted-foreground">Soon</span>
        )}
        {route.status === 'beta' && (
          <span className="text-[8px] font-bold uppercase px-1.5 py-0.5 bg-primary/10 text-primary rounded">Beta</span>
        )}
      </Link>
    )
  }

  // Multiple routes -> collapsible group
  return (
    <details open={isActive} className="group">
      <summary className={`
        flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-semibold cursor-pointer transition-all list-none
        ${isActive ? 'text-primary' : 'text-muted-foreground hover:bg-secondary hover:text-foreground'}
      `}>
        {sectionIconMap[section.key]}
        <span className="flex-1">{section.label}</span>
        <ChevronDown size={14} className="opacity-50 group-open:rotate-180 transition-transform" />
      </summary>
      <div className="ml-4 mt-0.5 space-y-0.5 border-l border-border pl-3">
        {routes.map(route => {
          const Icon = route.icon
          const isActiveRoute = location.pathname === route.path
          const disabled = isRouteDisabled(route.status)
          return (
            <Link
              key={route.path}
              to={disabled ? '#' : route.path}
              onClick={e => { if (disabled) e.preventDefault(); onNavigate?.() }}
              className={`
                flex items-center gap-2 px-2.5 py-1.5 rounded-md text-sm transition-all
                ${isActiveRoute ? 'bg-primary/10 text-primary font-medium' : disabled ? 'text-muted-foreground/50 cursor-not-allowed' : 'text-muted-foreground hover:bg-secondary hover:text-foreground'}
              `}
            >
              <Icon size={14} />
              <span className="flex-1">{route.label}</span>
              {route.status === 'coming_soon' && (
                <span className="text-[8px] font-bold uppercase px-1 py-0.5 bg-muted rounded text-muted-foreground">Soon</span>
              )}
              {route.status === 'beta' && (
                <span className="text-[8px] font-bold uppercase px-1 py-0.5 bg-primary/10 text-primary rounded">Beta</span>
              )}
            </Link>
          )
        })}
      </div>
    </details>
  )
}

export function Sidebar({ onNavigate }: SidebarProps) {
  return (
    <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-2">
      {navSections.map(section => (
        <SidebarSection key={section.key} section={section} onNavigate={onNavigate} />
      ))}
    </nav>
  )
}
