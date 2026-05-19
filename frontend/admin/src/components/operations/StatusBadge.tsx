import { CheckCircle2, AlertCircle, Clock, XCircle } from 'lucide-react'

interface StatusBadgeProps {
  status: string
  label?: string
}

export default function StatusBadge({ status, label }: StatusBadgeProps) {
  const config: Record<string, { color: string, icon: any }> = {
    healthy: { color: 'bg-green-100 text-green-700', icon: CheckCircle2 },
    ready: { color: 'bg-green-100 text-green-700', icon: CheckCircle2 },
    warning: { color: 'bg-amber-100 text-amber-700', icon: AlertCircle },
    investigating: { color: 'bg-amber-100 text-amber-700', icon: Clock },
    error: { color: 'bg-rose-100 text-rose-700', icon: XCircle },
    critical: { color: 'bg-rose-100 text-rose-700', icon: XCircle },
    draining: { color: 'bg-slate-100 text-slate-700', icon: Clock },
  }

  const { color, icon: Icon } = config[status.toLowerCase()] || { color: 'bg-slate-100 text-slate-600', icon: Clock }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${color}`}>
      <Icon className="w-3.5 h-3.5" />
      {label || status}
    </span>
  )
}
