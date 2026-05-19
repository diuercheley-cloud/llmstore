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
    healthy: 'text-teal-600 bg-teal-50',
    warning: 'text-amber-600 bg-amber-50',
    error: 'text-rose-600 bg-rose-50',
  }

  return (
    <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div className={`p-3 rounded-2xl ${statusColors[status]}`}>
          {icon}
        </div>
        {status !== 'healthy' && (
          <div className={`w-3 h-3 rounded-full animate-pulse ${status === 'warning' ? 'bg-amber-500' : 'bg-rose-500'}`}></div>
        )}
      </div>
      <div className="text-slate-500 text-xs font-bold uppercase tracking-widest mb-1">{title}</div>
      <div className="text-3xl font-black text-slate-900 mb-2">{value}</div>
      {description && <p className="text-slate-400 text-xs font-medium leading-relaxed">{description}</p>}
    </div>
  )
}
