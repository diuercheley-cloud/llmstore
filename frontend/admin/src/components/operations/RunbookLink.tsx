import { ExternalLink, BookOpen } from 'lucide-react'

interface RunbookLinkProps {
  href: string
  label?: string
}

export default function RunbookLink({ href, label = 'Ver Runbook' }: RunbookLinkProps) {
  return (
    <a 
      href={href} 
      target="_blank" 
      rel="noopener noreferrer"
      className="inline-flex items-center gap-2 text-primary hover:text-primary font-bold text-xs uppercase tracking-wider transition-colors"
    >
      <BookOpen className="w-3.5 h-3.5" />
      {label}
      <ExternalLink className="w-3 h-3" />
    </a>
  )
}
