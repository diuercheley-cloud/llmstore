import { useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, Bot, Clock, Coins, Download, Play, ShieldCheck, Zap } from 'lucide-react'
import { toast } from 'sonner'

import api from '../../lib/api'

export default function AgentObservability() {
  const queryClient = useQueryClient()
  const [selectedRun, setSelectedRun] = useState<string | null>(null)

  const { data: overview } = useQuery({
    queryKey: ['agent-observability-overview'],
    queryFn: () => api.getAgentObservabilityOverview(),
  })

  const { data: metricsSummary } = useQuery({
    queryKey: ['agent-observability-metrics-summary'],
    queryFn: () => api.getAgentObservabilityMetricsSummary(),
  })

  const { data: timeline } = useQuery({
    queryKey: ['agent-observability-timeline', selectedRun],
    queryFn: () => selectedRun ? api.getAgentRunTimeline(selectedRun) : [],
    enabled: !!selectedRun,
  })

  const { data: trace } = useQuery({
    queryKey: ['agent-observability-trace', selectedRun],
    queryFn: () => selectedRun ? api.getAgentRunTrace(selectedRun) : null,
    enabled: !!selectedRun,
  })

  const { data: telemetryStatus } = useQuery({
    queryKey: ['agent-observability-telemetry-status'],
    queryFn: () => api.getAgentTelemetryStatus(),
  })

  const replayMutation = useMutation({
    mutationFn: (runId: string) => api.replayAgentRun(runId),
    onSuccess: () => toast.success('Replay agendado com sucesso.'),
    onError: (error: any) => toast.error(error?.message || 'Falha ao iniciar replay'),
  })

  const exportTraceMutation = useMutation({
    mutationFn: () => api.exportAgentTrace(trace),
    onSuccess: result => {
      const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `agent-trace-${selectedRun || 'unknown'}.json`
      a.click()
      toast.success('Trace exportado.')
    },
    onError: (error: any) => toast.error(error?.message || 'Falha ao exportar trace'),
  })

  const recentRuns = Array.isArray(overview?.recent_runs) ? overview.recent_runs : []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-foreground">Agent Observability</h1>
        <p className="text-sm md:text-lg text-muted-foreground">Overview, timeline, trace, telemetry status e replay reais.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Total Runs" value={String(overview?.total_runs || 0)} icon={<Bot className="h-5 w-5" />} />
        <MetricCard label="Avg Latency" value={`${Number(metricsSummary?.avg_step_latency_ms || 0).toFixed(0)}ms`} icon={<Clock className="h-5 w-5 text-primary" />} />
        <MetricCard label="Tokens" value={Number(metricsSummary?.total_tokens || 0).toLocaleString()} icon={<Zap className="h-5 w-5" />} />
        <MetricCard label="Cost" value={`R$ ${Number(metricsSummary?.total_cost_brl || 0).toFixed(2)}`} icon={<Coins className="h-5 w-5 text-emerald-500" />} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr,1fr]">
        <Card title="Recent Runs">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs font-black uppercase tracking-widest text-muted-foreground">
                <th className="py-3 pr-4">Run</th>
                <th className="py-3 pr-4">Agent</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Steps</th>
                <th className="py-3 pr-4"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {recentRuns.map((run: any) => (
                <tr key={run.id}>
                  <td className="py-3 pr-4 font-mono text-xs text-muted-foreground">{String(run.id).slice(0, 12)}</td>
                  <td className="py-3 pr-4 text-foreground">{String(run.agent_id).slice(0, 12)}</td>
                  <td className="py-3 pr-4 text-foreground">{run.status}</td>
                  <td className="py-3 pr-4 text-foreground">{run.total_steps}</td>
                  <td className="py-3 pr-4">
                    <button type="button" onClick={() => setSelectedRun(run.id)} className="rounded-lg border border-border px-3 py-1 text-xs font-bold hover:bg-secondary">
                      Selecionar
                    </button>
                  </td>
                </tr>
              ))}
              {!recentRuns.length && (
                <tr><td colSpan={5} className="py-8 text-center text-muted-foreground">Nenhuma execucao recente.</td></tr>
              )}
            </tbody>
          </table>
        </Card>

        <Card title="Telemetry Status">
          <div className="space-y-4">
            <SummaryRow label="OTel tracing" value={telemetryStatus?.otel_tracing_enabled ? 'enabled' : 'disabled'} />
            <SummaryRow label="LangSmith export" value={telemetryStatus?.langsmith_export_enabled ? 'enabled' : 'disabled'} />
            <div className="rounded-2xl bg-background p-4 text-sm text-muted-foreground">
              Selecione um run para timeline, trace, replay e export.
            </div>
          </div>
        </Card>
      </div>

      {selectedRun && (
        <div className="grid gap-6 xl:grid-cols-[1fr,1fr]">
          <Card title={`Timeline ${selectedRun.slice(0, 12)}`}>
            <JsonList values={timeline || []} />
          </Card>
          <Card title="Trace">
            <div className="mb-4 flex gap-3">
              <button type="button" onClick={() => replayMutation.mutate(selectedRun)} className="rounded-xl border border-border px-4 py-2 text-sm font-bold hover:bg-secondary">
                <Play className="mr-2 inline h-4 w-4" />
                Replay
              </button>
              <button type="button" onClick={() => exportTraceMutation.mutate()} disabled={!trace} className="rounded-xl bg-primary px-4 py-2 text-sm font-bold text-white hover:bg-primary/90 disabled:opacity-50">
                <Download className="mr-2 inline h-4 w-4" />
                Exportar
              </button>
            </div>
            <pre className="overflow-x-auto rounded-2xl bg-background p-3 text-[10px] text-foreground">
              {JSON.stringify(trace || {}, null, 2)}
            </pre>
          </Card>
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, icon }: { label: string; value: string; icon: ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="mb-2 flex items-center gap-3 text-muted-foreground">{icon}</div>
      <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="text-2xl font-black text-foreground">{value}</div>
    </div>
  )
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-3xl border border-border bg-card p-5 shadow-sm">
      <div className="mb-4 text-lg font-black text-foreground">{title}</div>
      {children}
    </section>
  )
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-border bg-background px-4 py-3">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-black text-foreground">{value}</span>
    </div>
  )
}

function JsonList({ values }: { values: any[] }) {
  return (
    <div className="space-y-3">
      {values.length ? values.map((value, index) => (
        <pre key={index} className="overflow-x-auto rounded-2xl bg-background p-3 text-[10px] text-foreground">
          {JSON.stringify(value, null, 2)}
        </pre>
      )) : (
        <div className="rounded-2xl border border-dashed border-border p-6 text-sm text-muted-foreground">Nenhum registro.</div>
      )}
    </div>
  )
}
