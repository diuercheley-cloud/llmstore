import { ReactNode } from 'react'

interface EmptyStateProps {
  title: string
  description: string
  icon: ReactNode
}

export default function EmptyState({ title, description, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
      <div className="p-4 bg-slate-50 text-slate-300 rounded-3xl mb-6">
        {icon}
      </div>
      <h3 className="text-xl font-bold text-slate-900 mb-2">{title}</h3>
      <p className="text-slate-500 max-w-sm">{description}</p>
    </div>
  )
}
