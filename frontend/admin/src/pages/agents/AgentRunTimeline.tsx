import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Pause, Play, Square, Terminal } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { AgentRunTimelineComponent } from '../../components/agents/AgentRunTimelineComponent'
import { AgentStatusBadge } from '../../components/agents/AgentStatusBadge'
import { LoadingCard } from '../../components/ui-feedback'
import api from '../../lib/api'

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{label}</div>
      <div className="mt-2 break-all text-sm font-semibold text-foreground">{value}</div>
    </div>
  )
}

export default function AgentRunTimeline() {
  const { id } = useParams()
  const queryClient = useQueryClient()

  const runQuery = useQuery({
    queryKey: ['agent-run-admin', id],
    queryFn: () => api.getAdminAgentRun(id!),
    enabled: Boolean(id),
  })
  const stepsQuery = useQuery({
    queryKey: ['agent-run-steps-admin', id],
    queryFn: () => api.getAdminAgentRunSteps(id!),
    enabled: Boolean(id),
  })
  const timelineQuery = useQuery({
    queryKey: ['agent-run-timeline', id],
    queryFn: () => api.getAgentRunTimeline(id!),
    enabled: Boolean(id),
  })
  const traceQuery = useQuery({
    queryKey: ['agent-run-trace', id],
    queryFn: () => api.getAgentRunTrace(id!),
    enabled: Boolean(id),
  })
  const registryQuery = useQuery({
    queryKey: ['agent-registry'],
    queryFn: api.listAgentRegistry,
  })

  const agentNameById = useMemo(() => {
    const entries = registryQuery.data ?? []
    return new Map(entries.map((entry: any) => [String(entry.id), entry.name || entry.slug || String(entry.id)]))
  }, [registryQuery.data])

  const actionMutation = useMutation({
    mutationFn: async (action: 'pause' | 'resume' | 'cancel' | 'replay') => {
      if (!id) throw new Error('Run ID ausente')
      if (action === 'pause') return api.pauseAdminAgentRun(id)
      if (action === 'resume') return api.resumeAdminAgentRun(id)
      if (action === 'cancel') return api.cancelAdminAgentRun(id)
      return api.replayAgentRun(id)
    },
    onSuccess: (_, action) => {
      toast.success(`Acao ${action} executada.`)
      queryClient.invalidateQueries({ queryKey: ['agent-run-admin', id] })
      queryClient.invalidateQueries({ queryKey: ['agent-run-steps-admin', id] })
      queryClient.invalidateQueries({ queryKey: ['agent-run-timeline', id] })
    },
    onError: (error: any) => {
      toast.error(error.message || 'Falha ao executar acao no run.')
    },
  })

  if (runQuery.isLoading) return <LoadingCard />

  const run = runQuery.data
  const timelineItems = (timelineQuery.data ?? []).map((item: any, index: number) => ({ id: `${item.type}-${index}`, ...item }))
  const steps = stepsQuery.data ?? []
  const agentName = run ? agentNameById.get(String(run.agent_id)) || String(run.agent_id) : 'Unknown'
  const isPaused = run?.status === 'paused'
  const isTerminal = ['completed', 'failed', 'cancelled', 'rejected'].includes(String(run?.status))

  if (!run) {
    return (
      <div className="rounded-3xl border border-dashed border-border p-10 text-center text-muted-foreground">
        Run nao encontrado.
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <header>
        <Link to="/agents/runs" className="inline-flex items-center gap-2 text-sm font-semibold text-muted-foreground transition-colors hover:text-primary">
          <ArrowLeft className="h-4 w-4" />
          Voltar para runs
        </Link>
        <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Run Inspection</p>
            <h1 className="mt-2 break-all text-3xl font-black tracking-tight text-foreground">{run.id}</h1>
            <p className="mt-2 text-lg text-muted-foreground">Execucao do agente <span className="font-semibold text-foreground">{agentName}</span>.</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <AgentStatusBadge status={run.status || 'unknown'} />
            <button
              onClick={() => actionMutation.mutate('pause')}
              disabled={actionMutation.isPending || isPaused || isTerminal}
              className="inline-flex items-center gap-2 rounded-2xl border border-border px-4 py-2 text-sm font-semibold text-foreground transition-colors hover:bg-muted disabled:opacity-50"
            >
              <Pause className="h-4 w-4" />
              Pause
            </button>
            <button
              onClick={() => actionMutation.mutate('resume')}
              disabled={actionMutation.isPending || !isPaused}
              className="inline-flex items-center gap-2 rounded-2xl border border-border px-4 py-2 text-sm font-semibold text-foreground transition-colors hover:bg-muted disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              Resume
            </button>
            <button
              onClick={() => actionMutation.mutate('cancel')}
              disabled={actionMutation.isPending || isTerminal}
              className="inline-flex items-center gap-2 rounded-2xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 transition-colors hover:bg-red-100 disabled:opacity-50"
            >
              <Square className="h-4 w-4" />
              Cancel
            </button>
            <button
              onClick={() => actionMutation.mutate('replay')}
              disabled={actionMutation.isPending}
              className="inline-flex items-center gap-2 rounded-2xl bg-foreground px-4 py-2 text-sm font-semibold text-background transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              Replay
            </button>
          </div>
        </div>
      </header>

      {run.failure_reason && (
        <div className="rounded-3xl border border-red-200 bg-red-50 p-5 text-red-800">
          <div className="text-xs font-semibold uppercase tracking-[0.18em]">Failure Reason</div>
          <div className="mt-2 text-sm">{run.failure_reason}</div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="Agent" value={agentName} />
        <SummaryCard label="Tenant" value={run.tenant_id || 'N/A'} />
        <SummaryCard label="Started" value={run.started_at ? new Date(run.started_at).toLocaleString() : 'N/A'} />
        <SummaryCard label="Completed" value={run.completed_at ? new Date(run.completed_at).toLocaleString() : 'N/A'} />
        <SummaryCard label="Total Steps" value={String(run.total_steps ?? 0)} />
        <SummaryCard label="Total Tokens" value={String(run.total_tokens ?? 0)} />
        <SummaryCard label="Estimated Cost" value={typeof run.estimated_cost_brl === 'number' ? `R$ ${run.estimated_cost_brl.toFixed(2)}` : 'R$ 0.00'} />
        <SummaryCard label="Correlation ID" value={run.correlation_id || 'N/A'} />
      </div>

      <section className="rounded-3xl border border-border bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Timeline</div>
            <div className="mt-1 text-sm text-muted-foreground">Eventos, traces e passos consolidados.</div>
          </div>
          <Terminal className="h-5 w-5 text-muted-foreground" />
        </div>
        <div className="p-6">
          <AgentRunTimelineComponent items={timelineItems} />
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <section className="rounded-3xl border border-border bg-card p-6 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Steps</div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[700px] text-left">
              <thead>
                <tr className="border-b border-border text-[10px] font-black uppercase tracking-[0.24em] text-muted-foreground">
                  <th className="px-3 py-2">Step</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Latency</th>
                  <th className="px-3 py-2">Created</th>
                </tr>
              </thead>
              <tbody>
                {steps.map((step: any) => (
                  <tr key={step.id} className="border-b border-border/70 text-sm last:border-0">
                    <td className="px-3 py-3 text-muted-foreground">{step.step_number}</td>
                    <td className="px-3 py-3 font-medium text-foreground">{step.step_type}</td>
                    <td className="px-3 py-3"><AgentStatusBadge status={step.status || 'unknown'} /></td>
                    <td className="px-3 py-3 text-muted-foreground">{step.latency_ms ? `${step.latency_ms}ms` : 'N/A'}</td>
                    <td className="px-3 py-3 text-muted-foreground">{step.created_at ? new Date(step.created_at).toLocaleString() : 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!steps.length && (
              <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
                Nenhum step registrado para este run.
              </div>
            )}
          </div>
        </section>

        <section className="rounded-3xl border border-border bg-card p-6 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Trace</div>
          <pre className="mt-4 max-h-[640px] overflow-auto rounded-2xl bg-slate-950 p-4 text-xs text-slate-100">
            {JSON.stringify(traceQuery.data ?? {}, null, 2)}
          </pre>
        </section>
      </div>
    </div>
  )
}
