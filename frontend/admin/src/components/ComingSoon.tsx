import { Construction } from 'lucide-react'

interface ComingSoonProps {
  title: string
  description?: string
}

export default function ComingSoon({ title, description }: ComingSoonProps) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="p-4 bg-muted rounded-2xl mb-6">
        <Construction className="w-10 h-10 text-muted-foreground" />
      </div>
      <h1 className="text-2xl font-bold text-foreground mb-2">{title}</h1>
      <p className="text-muted-foreground max-w-md">
        {description || 'Esta funcionalidade está em desenvolvimento e estará disponível em breve.'}
      </p>
      <span className="mt-4 px-3 py-1 bg-primary/10 text-primary text-xs font-black uppercase tracking-wider rounded-full">
        Coming Soon
      </span>
    </div>
  )
}
