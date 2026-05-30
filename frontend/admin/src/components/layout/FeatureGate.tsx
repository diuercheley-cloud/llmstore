import { Construction, ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

interface FeatureGateProps {
  feature: string
  /** Custom message to show */
  message?: string
  /** If true, show a back link */
  showBack?: boolean
}

export function FeatureGate({ feature, message, showBack = true }: FeatureGateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="p-4 bg-muted rounded-2xl mb-6">
        <Construction className="w-10 h-10 text-muted-foreground" />
      </div>
      <h1 className="text-2xl font-bold text-foreground mb-2">Feature Coming Soon</h1>
      <p className="text-muted-foreground max-w-md mb-2">
        {message || `The "${feature}" feature is under development and will be available soon.`}
      </p>
      <span className="mb-6 px-3 py-1 bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider rounded-full">
        Coming Soon
      </span>
      {showBack && (
        <Link
          to="/"
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors"
        >
          <ArrowLeft size={14} />
          Back to Hub
        </Link>
      )}
    </div>
  )
}
