import type { ReactNode } from 'react'

interface EmptyStateProps {
  title: string
  description: string
  icon: ReactNode
}

export default function EmptyState({ title, description, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
      <div className="p-4 bg-secondary text-muted-foreground rounded-3xl mb-6">
        {icon}
      </div>
      <h3 className="text-xl font-bold text-foreground mb-2">{title}</h3>
      <p className="text-muted-foreground max-w-sm">{description}</p>
    </div>
  )
}
