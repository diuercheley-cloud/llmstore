import { ReactNode } from 'react'

interface HealthCardProps {
  title: string
  value: string | number
  status?: 'healthy' | 'warning' | 'error'
  icon: ReactNode
  description?: string
}

export default function HealthCard({ title, value, status = 'healthy', icon, description }: HealthCardProps) {
  const statusColors = {
    healthy: 'text-primary bg-primary/10',
    warning: 'text-yellow-600 bg-yellow-500/10',
    error: 'text-destructive bg-destructive/10',
  }

  return (
    <div className="bg-card p-6 rounded-3xl border border-border shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div className={`p-3 rounded-2xl ${statusColors[status]}`}>
          {icon}
        </div>
        {status !== 'healthy' && (
          <div className={`w-3 h-3 rounded-full animate-pulse ${status === 'warning' ? 'bg-yellow-500/100' : 'bg-destructive'}`}></div>
        )}
      </div>
      <div className="text-muted-foreground text-xs font-bold uppercase tracking-widest mb-1">{title}</div>
      <div className="text-3xl font-black text-foreground mb-2">{value}</div>
      {description && <p className="text-muted-foreground text-xs font-medium leading-relaxed">{description}</p>}
    </div>
  )
}
