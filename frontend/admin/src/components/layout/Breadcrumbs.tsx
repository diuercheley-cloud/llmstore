import { Link, useLocation } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { buildBreadcrumbs } from '../../navigation/navConfig'

export function Breadcrumbs() {
  const location = useLocation()
  const crumbs = buildBreadcrumbs(location.pathname)

  if (crumbs.length === 0) return null

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-xs text-muted-foreground mb-6">
      <Link to="/" className="hover:text-primary transition-colors font-semibold">Hub</Link>
      {crumbs.map((crumb, i) => (
        <span key={crumb.path} className="flex items-center gap-1">
          <ChevronRight size={12} className="opacity-40" />
          {i === crumbs.length - 1 ? (
            <span className="text-foreground font-semibold">{crumb.label}</span>
          ) : (
            <Link to={crumb.path} className="hover:text-primary transition-colors">{crumb.label}</Link>
          )}
        </span>
      ))}
    </nav>
  )
}
