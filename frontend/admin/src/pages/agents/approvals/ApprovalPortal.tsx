import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Inbox, Search } from 'lucide-react'
import { toast } from 'sonner'
import ApprovalDetail from './ApprovalDetail'
import { AgentStatusBadge } from '../../../components/agents/AgentStatusBadge'
import { LoadingCard } from '../../../components/ui-feedback'
import api from '../../../lib/api'

type ApprovalAction = 'approve' | 'reject' | 'request_changes'

const inputClassName = 'rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary'

export default function ApprovalPortal() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('pending')

  const approvalsQuery = useQuery({
    queryKey: ['agent-approvals-admin', status],
    queryFn: () => api.listAgentApprovalsAdmin(status ? { status, limit: 100 } : { limit: 100 }),
  })

  const approvals = approvalsQuery.data ?? []
  const filteredApprovals = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return approvals
    return approvals.filter((approval: any) =>
      [
        approval.id,
        approval.agent_run_id,
        approval.requested_by,
        approval.reason,
        approval.risk_level,
        approval.status,
        approval.sanitized_context?.tool_name,
      ].some(value => String(value ?? '').toLowerCase().includes(term)),
    )
  }, [approvals, search])

  useEffect(() => {
    if (!filteredApprovals.length) {
      setSelectedId(null)
      return
    }
    if (!selectedId || !filteredApprovals.some((approval: any) => approval.id === selectedId)) {
      setSelectedId(filteredApprovals[0].id)
    }
  }, [filteredApprovals, selectedId])

  const detailQuery = useQuery({
    queryKey: ['agent-approval-admin', selectedId],
    queryFn: () => api.getAgentApprovalAdmin(selectedId!),
    enabled: Boolean(selectedId),
  })

  const actionMutation = useMutation({
    mutationFn: async ({ id, action, reason }: { id: string; action: ApprovalAction; reason: string }) => {
      if (action === 'approve') return api.approveAgentApprovalAdmin(id, reason)
      if (action === 'reject') return api.rejectAgentApprovalAdmin(id, reason)
      return api.requestChangesAgentApprovalAdmin(id, reason)
    },
    onSuccess: (_, variables) => {
      toast.success(`Approval ${variables.action} executado.`)
      queryClient.invalidateQueries({ queryKey: ['agent-approvals-admin'] })
      queryClient.invalidateQueries({ queryKey: ['agent-approval-admin'] })
    },
    onError: (error: any) => {
      toast.error(error.message || 'Falha ao processar a aprovacao.')
    },
  })

  const selectedApproval = detailQuery.data || filteredApprovals.find((approval: any) => approval.id === selectedId)

  if (approvalsQuery.isLoading) return <LoadingCard />

  return (
    <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
      <section className="rounded-3xl border border-border bg-card p-6 shadow-sm">
        <header className="mb-6 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Human In The Loop</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-foreground">Approval Portal</h1>
            <p className="mt-2 text-sm text-muted-foreground">Inbox operacional para aprovar, rejeitar ou pedir ajustes.</p>
          </div>
          <div className="rounded-2xl bg-primary/10 p-3 text-primary">
            <Inbox className="h-6 w-6" />
          </div>
        </header>

        <div className="grid gap-3">
          <label className="grid gap-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Search</span>
            <div className="relative">
              <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                value={search}
                onChange={event => setSearch(event.target.value)}
                className={`${inputClassName} w-full pl-11`}
                placeholder="ID, tool, run, requested by..."
              />
            </div>
          </label>

          <label className="grid gap-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Status</span>
            <select value={status} onChange={event => setStatus(event.target.value)} className={inputClassName}>
              <option value="pending">pending</option>
              <option value="approved">approved</option>
              <option value="rejected">rejected</option>
              <option value="changes_requested">changes_requested</option>
              <option value="">all</option>
            </select>
          </label>
        </div>

        <div className="mt-6 space-y-3">
          {filteredApprovals.map((approval: any) => (
            <button
              key={approval.id}
              onClick={() => setSelectedId(approval.id)}
              className={`w-full rounded-2xl border p-4 text-left transition-colors ${
                selectedId === approval.id ? 'border-primary bg-primary/5' : 'border-border bg-background/70 hover:bg-muted/40'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate font-mono text-xs text-muted-foreground">{approval.id}</div>
                  <div className="mt-2 line-clamp-2 text-sm font-semibold text-foreground">{approval.reason}</div>
                  <div className="mt-2 text-xs text-muted-foreground">{approval.sanitized_context?.tool_name || 'tool unavailable'}</div>
                </div>
                <AgentStatusBadge status={approval.status || 'unknown'} />
              </div>
              <div className="mt-3 flex items-center justify-between gap-3 text-xs text-muted-foreground">
                <span>{approval.risk_level || 'unknown'}</span>
                <span>{approval.created_at ? new Date(approval.created_at).toLocaleString() : 'N/A'}</span>
              </div>
            </button>
          ))}

          {!filteredApprovals.length && (
            <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
              Nenhuma aprovacao encontrada para o filtro atual.
            </div>
          )}
        </div>
      </section>

      <section>
        {selectedApproval ? (
          <ApprovalDetail
            approval={selectedApproval}
            busyAction={actionMutation.isPending ? actionMutation.variables?.action ?? null : null}
            onAction={(action, reason) => actionMutation.mutate({ id: selectedApproval.id, action, reason })}
          />
        ) : (
          <div className="flex min-h-[420px] items-center justify-center rounded-3xl border border-dashed border-border bg-card p-10 text-center text-muted-foreground">
            Selecione uma aprovacao para revisar os detalhes.
          </div>
        )}
      </section>
    </div>
  )
}
