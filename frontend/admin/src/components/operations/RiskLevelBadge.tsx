interface RiskLevelBadgeProps {
  level: string
}

export default function RiskLevelBadge({ level }: RiskLevelBadgeProps) {
  const config: Record<string, string> = {
    low: 'bg-primary/20 text-primary',
    medium: 'bg-yellow-500/20 text-yellow-600',
    high: 'bg-destructive/20 text-destructive',
    critical: 'bg-destructive text-white',
  }

  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-tighter ${config[level.toLowerCase()] || 'bg-secondary'}`}>
      {level}
    </span>
  )
}
