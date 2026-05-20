import { ReactNode } from 'react'

interface ActionPanelProps {
  title: string
  description: string
  children: ReactNode
}

export default function ActionPanel({ title, description, children }: ActionPanelProps) {
  return (
    <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
      <h3 className="text-lg font-bold text-foreground mb-1">{title}</h3>
      <p className="text-muted-foreground text-sm mb-6">{description}</p>
      <div className="flex flex-wrap gap-3">
        {children}
      </div>
    </div>
  )
}
