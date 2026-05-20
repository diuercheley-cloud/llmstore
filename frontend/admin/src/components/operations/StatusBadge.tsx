import { CheckCircle2, AlertCircle, Clock, XCircle } from 'lucide-react'

interface StatusBadgeProps {
  status: string
  label?: string
}

export default function StatusBadge({ status, label }: StatusBadgeProps) {
  const config: Record<string, { color: string, icon: any }> = {
    healthy: { color: 'bg-primary/20 text-primary', icon: CheckCircle2 },
    ready: { color: 'bg-primary/20 text-primary', icon: CheckCircle2 },
    warning: { color: 'bg-yellow-500/20 text-yellow-600', icon: AlertCircle },
    investigating: { color: 'bg-yellow-500/20 text-yellow-600', icon: Clock },
    error: { color: 'bg-destructive/20 text-destructive', icon: XCircle },
    critical: { color: 'bg-destructive/20 text-destructive', icon: XCircle },
    draining: { color: 'bg-secondary text-foreground', icon: Clock },
  }

  const { color, icon: Icon } = config[status.toLowerCase()] || { color: 'bg-secondary text-muted-foreground', icon: Clock }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${color}`}>
      <Icon className="w-3.5 h-3.5" />
      {label || status}
    </span>
  )
}
