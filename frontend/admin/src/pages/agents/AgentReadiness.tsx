import { useMutation, useQuery } from '@tanstack/react-query'
import { CheckCircle2, RefreshCw } from 'lucide-react'
import { JsonPanel, MetricCard, SectionCard } from '../../components/admin/AdminSurface'
import { LoadingCard } from '../../components/ui-feedback'
import api from '../../lib/api'

export default function AgentReadiness() {
  const readinessQuery = useQuery({ queryKey: ['agent-readiness'], queryFn: api.getAgentReadiness })
  const runMutation = useMutation({ mutationFn: api.runAgentReadiness })

  if (readinessQuery.isLoading) return <LoadingCard />

  const data = runMutation.data ?? readinessQuery.data ?? {}
  const checks = Array.isArray((data as any)?.checks) ? (data as any).checks : []

  return (
    <div className="space-y-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Runtime Health</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight text-foreground">Agent Readiness</h1>
          <p className="mt-2 text-lg text-muted-foreground">Readiness consolidado do runtime agentic e dos seus prerequisitos.</p>
        </div>
        <div className="rounded-3xl bg-primary/10 p-4 text-primary">
          <CheckCircle2 className="h-8 w-8" />
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Checks" value={String(checks.length)} />
        <MetricCard label="Ready" value={String((data as any)?.ready ?? (data as any)?.status ?? 'unknown')} />
        <MetricCard label="Source" value={runMutation.data ? 'fresh' : 'cached'} />
      </div>

      <SectionCard
        title="Readiness Snapshot"
        subtitle="GET e POST /admin/agents/readiness"
        actions={
          <button onClick={() => runMutation.mutate()} className="inline-flex items-center gap-2 rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">
            <RefreshCw className="h-4 w-4" />
            Run Check
          </button>
        }
      >
        <JsonPanel data={data} />
      </SectionCard>
    </div>
  )
}
