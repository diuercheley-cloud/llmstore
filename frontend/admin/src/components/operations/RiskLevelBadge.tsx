interface RiskLevelBadgeProps {
  level: string
}

export default function RiskLevelBadge({ level }: RiskLevelBadgeProps) {
  const config: Record<string, string> = {
    low: 'bg-green-100 text-green-700',
    medium: 'bg-amber-100 text-amber-700',
    high: 'bg-rose-100 text-rose-700',
    critical: 'bg-rose-600 text-white',
  }

  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-tighter ${config[level.toLowerCase()] || 'bg-slate-100'}`}>
      {level}
    </span>
  )
}
