import { useMutation, useQuery } from '@tanstack/react-query'
import { Activity, RefreshCw } from 'lucide-react'
import { JsonPanel, MetricCard, SectionCard } from '../../components/admin/AdminSurface'
import { LoadingCard } from '../../components/ui-feedback'
import api from '../../lib/api'

export default function AIOpsDashboard() {
  const statusQuery = useQuery({ queryKey: ['aiops-status'], queryFn: api.getAIOpsStatus })
  const forecastsQuery = useQuery({ queryKey: ['aiops-forecasts'], queryFn: () => api.getAIOpsForecasts() })
  const anomaliesQuery = useQuery({ queryKey: ['aiops-anomalies'], queryFn: () => api.getAIOpsAnomalies() })
  const recommendationsQuery = useQuery({ queryKey: ['aiops-recommendations'], queryFn: () => api.getAIOpsRecommendations() })
  const risksQuery = useQuery({ queryKey: ['aiops-risk-trends'], queryFn: () => api.getAIOpsRiskTrends() })
  const runMutation = useMutation({ mutationFn: api.runAIOpsCycle })

  if (statusQuery.isLoading) return <LoadingCard />

  return (
    <div className="space-y-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Predictive Ops</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight text-foreground">AIOps</h1>
          <p className="mt-2 text-lg text-muted-foreground">Status, forecasts, anomalies, recommendations e risk trends do ciclo preditivo.</p>
        </div>
        <div className="rounded-3xl bg-primary/10 p-4 text-primary">
          <Activity className="h-8 w-8" />
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-5">
        <MetricCard label="Forecasts" value={String((forecastsQuery.data ?? []).length)} />
        <MetricCard label="Anomalies" value={String((anomaliesQuery.data ?? []).length)} />
        <MetricCard label="Recommendations" value={String((recommendationsQuery.data ?? []).length)} />
        <MetricCard label="Risk Trends" value={String((risksQuery.data ?? []).length)} />
        <MetricCard label="Cycle" value={runMutation.data ? 'fresh' : 'cached'} />
      </div>

      <SectionCard
        title="Status"
        subtitle="GET /admin/aiops/status"
        actions={
          <button onClick={() => runMutation.mutate()} className="inline-flex items-center gap-2 rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">
            <RefreshCw className="h-4 w-4" />
            Run Cycle
          </button>
        }
      >
        <JsonPanel data={runMutation.data ?? statusQuery.data} />
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Forecasts" subtitle="Capacidade preditiva recente.">
          <JsonPanel data={forecastsQuery.data} />
        </SectionCard>
        <SectionCard title="Anomalies" subtitle="Anomalias recentes detectadas.">
          <JsonPanel data={anomaliesQuery.data} />
        </SectionCard>
        <SectionCard title="Recommendations" subtitle="Acoes sugeridas pelo motor.">
          <JsonPanel data={recommendationsQuery.data} />
        </SectionCard>
        <SectionCard title="Risk Trends" subtitle="Curvas e sinais de risco.">
          <JsonPanel data={risksQuery.data} />
        </SectionCard>
      </div>
    </div>
  )
}
