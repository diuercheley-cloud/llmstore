import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  icon?: ReactNode
  badge?: string
  badgeVariant?: 'default' | 'success' | 'warning' | 'error' | 'beta'
  actions?: ReactNode
}

const badgeStyles: Record<string, string> = {
  default: 'bg-secondary text-muted-foreground border-border',
  success: 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800',
  warning: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800',
  error: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800',
  beta: 'bg-primary/10 text-primary border-primary/20',
}

export function PageHeader({ title, subtitle, icon, badge, badgeVariant = 'default', actions }: PageHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
      <div className="flex items-center gap-4">
        {icon && (
          <div className="p-2.5 bg-primary/10 text-primary rounded-xl">
            {icon}
          </div>
        )}
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">{title}</h1>
            {badge && (
              <span className={`px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full border ${badgeStyles[badgeVariant]}`}>
                {badge}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>
          )}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
