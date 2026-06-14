import { useState } from 'react'
import { ShieldAlert } from 'lucide-react'
import { AgentStatusBadge } from '../../../components/agents/AgentStatusBadge'

type ApprovalRecord = {
  id: string
  agent_run_id?: string
  agent_name?: string
  risk_level?: string
  reviewer_role?: string
  requested_by?: string
  status?: string
  reason?: string
  expires_at?: string
  created_at?: string
  decision_reason?: string | null
  sanitized_context?: {
    tool_name?: string
    tool_input?: unknown
  }
}

type ApprovalAction = 'approve' | 'reject' | 'request_changes'

function riskBadgeClass(riskLevel?: string) {
  if (riskLevel === 'critical' || riskLevel === 'high') return 'bg-red-100 text-red-700'
  if (riskLevel === 'medium') return 'bg-amber-100 text-amber-700'
  return 'bg-slate-100 text-slate-700'
}

function formatDate(value?: string | null) {
  if (!value) return 'N/A'
  return new Date(value).toLocaleString()
}

export default function ApprovalDetail({
  approval,
  busyAction,
  onAction,
}: {
  approval: ApprovalRecord
  busyAction?: ApprovalAction | null
  onAction: (action: ApprovalAction, reason: string) => void
}) {
  const [reason, setReason] = useState('')

  return (
    <section className="rounded-3xl border border-border bg-card p-6 shadow-sm">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Approval Request</p>
          <h2 className="mt-2 text-xl font-semibold text-foreground break-all">{approval.id}</h2>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase ${riskBadgeClass(approval.risk_level)}`}>
          {approval.risk_level || 'unknown'}
        </span>
      </header>

      <dl className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-border bg-background/70 p-4">
          <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Status</dt>
          <dd className="mt-2"><AgentStatusBadge status={approval.status || 'unknown'} /></dd>
        </div>
        <div className="rounded-2xl border border-border bg-background/70 p-4">
          <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Agent Run</dt>
          <dd className="mt-2 break-all text-sm text-foreground">{approval.agent_run_id || 'N/A'}</dd>
        </div>
        <div className="rounded-2xl border border-border bg-background/70 p-4">
          <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Requested By</dt>
          <dd className="mt-2 text-sm text-foreground">{approval.requested_by || 'Unknown'}</dd>
        </div>
        <div className="rounded-2xl border border-border bg-background/70 p-4">
          <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Reviewer Role</dt>
          <dd className="mt-2 text-sm text-foreground">{approval.reviewer_role || 'N/A'}</dd>
        </div>
        <div className="rounded-2xl border border-border bg-background/70 p-4">
          <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Created</dt>
          <dd className="mt-2 text-sm text-foreground">{formatDate(approval.created_at)}</dd>
        </div>
        <div className="rounded-2xl border border-border bg-background/70 p-4">
          <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Expires</dt>
          <dd className="mt-2 text-sm text-foreground">{formatDate(approval.expires_at)}</dd>
        </div>
        <div className="rounded-2xl border border-border bg-background/70 p-4 md:col-span-2">
          <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Reason</dt>
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

      {approval.decision_reason && (
        <div className="mt-6 rounded-2xl border border-border bg-background/70 p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Previous Decision Reason</div>
          <div className="mt-2 text-sm text-foreground">{approval.decision_reason}</div>
        </div>
      )}

      <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50/70 p-4 text-amber-900">
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" />
          <div className="space-y-3">
            <div className="text-sm font-semibold">Decision reason</div>
            <textarea
              value={reason}
              onChange={event => setReason(event.target.value)}
              className="min-h-24 w-full rounded-2xl border border-amber-200 bg-white px-4 py-3 text-sm text-foreground outline-none focus:border-amber-400"
              placeholder="Motivo para aprovar, rejeitar ou solicitar ajustes."
            />
          </div>
        </div>
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        <button
          onClick={() => onAction('approve', reason)}
          disabled={busyAction !== null}
          className="rounded-2xl bg-foreground px-5 py-3 text-sm font-semibold text-background transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          {busyAction === 'approve' ? 'Aprovando...' : 'Approve'}
        </button>
        <button
          onClick={() => onAction('reject', reason)}
          disabled={busyAction !== null}
          className="rounded-2xl border border-red-300 bg-red-50 px-5 py-3 text-sm font-semibold text-red-700 transition-colors hover:bg-red-100 disabled:opacity-60"
        >
          {busyAction === 'reject' ? 'Rejecting...' : 'Reject'}
        </button>
        <button
          onClick={() => onAction('request_changes', reason)}
          disabled={busyAction !== null}
          className="rounded-2xl border border-border bg-background px-5 py-3 text-sm font-semibold text-foreground transition-colors hover:bg-muted disabled:opacity-60"
        >
          {busyAction === 'request_changes' ? 'Requesting...' : 'Request Changes'}
        </button>
      </div>
    </section>
  )
}
