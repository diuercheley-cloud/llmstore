import { GitBranch, CheckCircle2, Clock } from 'lucide-react'

interface LineageEntry {
  version: string
  title: string
  date: string
  author: string
  active: boolean
}

const entries: LineageEntry[] = [
  { version: 'v1.2.1', title: 'Promoted to production', date: '2026-05-22 10:00', author: 'admin@company.com', active: true },
  { version: 'v1.2.0', title: 'Eval Baseline Set', date: '2026-05-21 14:30', author: 'system', active: true },
  { version: 'v1.1.0', title: 'Policy Updated', date: '2026-05-20 09:00', author: 'admin@company.com', active: true },
  { version: 'v1.0.0', title: 'Initial Release', date: '2026-05-18 08:00', author: 'admin@company.com', active: false },
]

export default function AgentLineage() {
  return (
    <div className="space-y-6">
      <header>
        <div className="flex items-center gap-2 text-primary font-bold uppercase tracking-wider text-xs mb-2">
          <GitBranch className="w-4 h-4" />
          Agent Lifecycle
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight">Agent Lineage</h1>
      </header>

      <div className="bg-card border border-border rounded-2xl p-6">
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[11px] top-0 bottom-0 w-0.5 bg-border" />

          <div className="space-y-6">
            {entries.map((entry, i) => (
              <div key={entry.version} className="flex gap-4 relative">
                <div className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                  entry.active ? 'bg-primary text-white' : 'bg-muted text-muted-foreground'
                }`}>
                  {i === 0 ? <CheckCircle2 size={14} /> : <Clock size={14} />}
                </div>
                <div className="flex-1 pb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-sm">{entry.version}</span>
                    <span className="text-muted-foreground text-sm">-</span>
                    <span className="text-sm">{entry.title}</span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {entry.date} &middot; {entry.author}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
