type ApprovalRecord = {
  id: string
  agent_name?: string
  risk_level?: string
  reason?: string
  sanitized_context?: {
    tool_name?: string
    tool_input?: unknown
  }
}

function riskBadgeClass(riskLevel?: string) {
  if (riskLevel === 'critical' || riskLevel === 'high') return 'bg-red-100 text-red-700'
  if (riskLevel === 'medium') return 'bg-amber-100 text-amber-700'
  return 'bg-slate-100 text-slate-700'
}

export default function ApprovalDetail({ approval }: { approval: ApprovalRecord }) {
  return (
    <section className="rounded-3xl border border-border bg-card p-6 shadow-sm">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Approval Request</p>
          <h2 className="mt-2 text-2xl font-semibold text-foreground">{approval.id}</h2>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase ${riskBadgeClass(approval.risk_level)}`}>
          {approval.risk_level || 'unknown'}
        </span>
      </header>

      <dl className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-border bg-background/70 p-4">
          <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Agent</dt>
          <dd className="mt-2 text-sm text-foreground">{approval.agent_name || 'Unknown agent'}</dd>
        </div>
        <div className="rounded-2xl border border-border bg-background/70 p-4">
          <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Requested Reason</dt>
          <dd className="mt-2 text-sm text-foreground">{approval.reason || 'No reason provided.'}</dd>
        </div>
        <div className="rounded-2xl border border-border bg-background/70 p-4 md:col-span-2">
          <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Tool</dt>
          <dd className="mt-2 text-sm text-foreground">{approval.sanitized_context?.tool_name || 'Unavailable'}</dd>
        </div>
        <div className="rounded-2xl border border-border bg-background/70 p-4 md:col-span-2">
          <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Sanitized Input</dt>
          <dd className="mt-3 overflow-x-auto rounded-2xl bg-slate-950 p-4 text-xs text-slate-100">
            <pre>{JSON.stringify(approval.sanitized_context?.tool_input ?? {}, null, 2)}</pre>
          </dd>
        </div>
      </dl>

      <div className="mt-8 flex flex-wrap gap-3">
        <button className="rounded-2xl bg-foreground px-5 py-3 text-sm font-semibold text-background transition-opacity hover:opacity-90">
          Approve
        </button>
        <button className="rounded-2xl border border-red-300 bg-red-50 px-5 py-3 text-sm font-semibold text-red-700 transition-colors hover:bg-red-100">
          Reject
        </button>
        <button className="rounded-2xl border border-border bg-background px-5 py-3 text-sm font-semibold text-foreground transition-colors hover:bg-muted">
          Request Changes
        </button>
      </div>
    </section>
  )
}
