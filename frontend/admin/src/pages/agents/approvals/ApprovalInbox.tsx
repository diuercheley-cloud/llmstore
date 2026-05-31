import { useMemo, useState } from 'react'

type ApprovalItem = {
  id: string
  agent_name: string
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  reason: string
  expires_at: string
  tenant_id?: string
}

const demoApprovals: ApprovalItem[] = [
  {
    id: 'apr_001',
    agent_name: 'Finance Ops Agent',
    risk_level: 'critical',
    reason: 'Transferencia de saldo acima do limite automatico.',
    expires_at: '2026-06-01T10:30:00Z',
    tenant_id: 'tenant-finance',
  },
  {
    id: 'apr_002',
    agent_name: 'Support Escalation Agent',
    risk_level: 'high',
    reason: 'Abertura de incidente externo com acao destrutiva.',
    expires_at: '2026-06-01T11:00:00Z',
    tenant_id: 'tenant-support',
  },
]

function riskBadgeClass(riskLevel: ApprovalItem['risk_level']) {
  if (riskLevel === 'critical' || riskLevel === 'high') return 'bg-red-100 text-red-700'
  if (riskLevel === 'medium') return 'bg-amber-100 text-amber-700'
  return 'bg-emerald-100 text-emerald-700'
}

export default function ApprovalInbox() {
  const [risk, setRisk] = useState<'all' | ApprovalItem['risk_level']>('all')
  const [tenant, setTenant] = useState('')

  const approvals = useMemo(() => {
    return demoApprovals.filter(item => {
      const riskMatch = risk === 'all' || item.risk_level === risk
      const tenantMatch = !tenant || item.tenant_id?.toLowerCase().includes(tenant.toLowerCase())
      return riskMatch && tenantMatch
    })
  }, [risk, tenant])

  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">HITL Operations</p>
        <h1 className="text-3xl font-semibold text-foreground">Approval Inbox</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Fila operacional para revisar acoes bloqueadas por politica, risco ou sandbox.
        </p>
      </header>

      <div className="grid gap-4 rounded-3xl border border-border bg-card p-5 md:grid-cols-[220px_1fr]">
        <label className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Risk level</span>
          <select
            value={risk}
            onChange={event => setRisk(event.target.value as 'all' | ApprovalItem['risk_level'])}
            className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none"
          >
            <option value="all">All risks</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </label>
        <label className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Tenant</span>
          <input
            value={tenant}
            onChange={event => setTenant(event.target.value)}
            placeholder="Filter by tenant"
            className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none"
          />
        </label>
      </div>

      <div className="overflow-hidden rounded-3xl border border-border bg-card">
        <table className="min-w-full divide-y divide-border text-sm">
          <thead className="bg-muted/60 text-left text-xs uppercase tracking-[0.18em] text-muted-foreground">
            <tr>
              <th className="px-5 py-4">ID</th>
              <th className="px-5 py-4">Agent</th>
              <th className="px-5 py-4">Risk</th>
              <th className="px-5 py-4">Reason</th>
              <th className="px-5 py-4">Expires</th>
              <th className="px-5 py-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {approvals.map(approval => (
              <tr key={approval.id} className="align-top">
                <td className="px-5 py-4 font-mono text-xs text-muted-foreground">{approval.id}</td>
                <td className="px-5 py-4 text-foreground">{approval.agent_name}</td>
                <td className="px-5 py-4">
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase ${riskBadgeClass(approval.risk_level)}`}>
                    {approval.risk_level}
                  </span>
                </td>
                <td className="px-5 py-4 text-muted-foreground">{approval.reason}</td>
                <td className="px-5 py-4 text-muted-foreground">{approval.expires_at}</td>
                <td className="px-5 py-4">
                  <div className="flex flex-wrap gap-2">
                    <button className="rounded-xl bg-foreground px-3 py-2 text-xs font-semibold text-background transition-opacity hover:opacity-90">
                      Review
                    </button>
                    <button className="rounded-xl border border-red-300 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 transition-colors hover:bg-red-100">
                      Reject
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {approvals.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-10 text-center text-sm text-muted-foreground">
                  Nenhuma aprovacao corresponde aos filtros atuais.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
