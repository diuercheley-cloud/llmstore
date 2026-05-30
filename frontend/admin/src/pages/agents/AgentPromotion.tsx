import { Rocket, CheckCircle2, XCircle, ShieldCheck } from 'lucide-react'

interface GateStatus {
  label: string
  detail: string
  passed: boolean
}

const gates: GateStatus[] = [
  { label: 'Evaluation Results', detail: 'Latest pass rate: 98% (Goal: 95%)', passed: true },
  { label: 'Human Approval', detail: 'Approved by security-lead@company.com', passed: true },
  { label: 'Active Incidents', detail: '1 open critical incident detected', passed: false },
]

export default function AgentPromotion() {
  const allPassed = gates.every(g => g.passed)

  return (
    <div className="space-y-6">
      <header>
        <div className="flex items-center gap-2 text-primary font-bold uppercase tracking-wider text-xs mb-2">
          <Rocket className="w-4 h-4" />
          Agent Lifecycle
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight">Agent Promotion</h1>
      </header>

      <div className="bg-card border border-border rounded-2xl p-6 space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <ShieldCheck className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-bold">Target: production</h2>
            <p className="text-sm text-muted-foreground">Promotion gates must all pass before deploying.</p>
          </div>
        </div>

        <div className="space-y-3">
          {gates.map(gate => (
            <div key={gate.label} className="flex items-start gap-3 p-3 rounded-xl bg-secondary/50">
              {gate.passed ? (
                <CheckCircle2 className="w-5 h-5 text-green-500 mt-0.5 shrink-0" />
              ) : (
                <XCircle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
              )}
              <div>
                <div className="font-semibold text-sm">{gate.label}</div>
                <div className="text-xs text-muted-foreground">{gate.detail}</div>
              </div>
            </div>
          ))}
        </div>

        <div>
          <button
            disabled={!allPassed}
            className={`px-6 py-3 rounded-xl font-bold text-sm transition-all ${
              allPassed
                ? 'bg-primary text-white hover:bg-primary/90 shadow-sm'
                : 'bg-muted text-muted-foreground cursor-not-allowed'
            }`}
          >
            Promote to Production
          </button>
          {!allPassed && (
            <p className="mt-2 text-xs text-red-500 font-medium">
              Promotion blocked due to active critical incidents.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
