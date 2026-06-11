import { useMemo } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { BadgeCheck, BarChart3, Brain, Clock3, FileDown, PlayCircle, ShieldAlert, Sigma, Wrench } from 'lucide-react'
import { toast } from 'sonner'
import api from '../../lib/api'

export default function AgentEvaluation() {
  const benchmarks = useQuery({
    queryKey: ['agent-evaluation-benchmarks'],
    queryFn: async () => api.listAgentBenchmarks(),
  })

  const reports = useQuery({
    queryKey: ['agent-evaluation-reports'],
    queryFn: async () => api.listAgentBenchmarkReports(),
  })

  const runMutation = useMutation({
    mutationFn: async (payload: { agent_id: string; model_name: string; benchmark: string }) => (await api.runAgentBenchmark(payload)).data,
    onSuccess: () => {
      toast.success('Benchmark executado.')
      reports.refetch()
    },
    onError: (err: any) => toast.error(err?.message || 'Falha ao executar benchmark'),
  })

  const latestReport = useMemo(() => reports.data?.[0], [reports.data])

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-foreground flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-primary" /> Agent Evaluation
          </h1>
          <p className="text-muted-foreground mt-1">Avaliação automática de agentes com AgentBench, GAIA e BFCL.</p>
        </div>
        <button
          onClick={() => runMutation.mutate({ agent_id: '00000000-0000-0000-0000-000000000000', model_name: 'demo-model', benchmark: 'AgentBench' })}
          className="flex items-center gap-2 px-5 py-3 rounded-xl bg-primary text-primary-foreground font-black"
        >
          <PlayCircle className="w-4 h-4" /> Run benchmark
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {[
          ['Success rate', latestReport?.metrics?.success_rate],
          ['Tool efficiency', latestReport?.metrics?.tool_efficiency],
          ['Latency (ms)', latestReport?.metrics?.latency_ms],
          ['Token cost', latestReport?.metrics?.token_cost],
          ['Hallucination', latestReport?.metrics?.hallucination_score],
        ].map(([label, value]) => (
          <div key={label as string} className="p-5 rounded-2xl border border-border bg-card">
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-black">{label}</div>
            <div className="text-2xl font-black mt-2 text-primary">{value === undefined ? '—' : typeof value === 'number' && value < 1 ? `${(value as number * 100).toFixed(1)}%` : value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {benchmarks.data?.map((b: any) => (
          <div key={b.name} className="p-6 rounded-3xl border border-border bg-card space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-black text-lg">{b.name}</h3>
              <BadgeCheck className="w-5 h-5 text-emerald-500" />
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="p-3 rounded-xl bg-secondary/20"><div className="text-xs uppercase text-muted-foreground">Tasks</div><div className="font-black">{b.tasks}</div></div>
              <div className="p-3 rounded-xl bg-secondary/20"><div className="text-xs uppercase text-muted-foreground">Vision</div><div className="font-black">{String(!!b.supports?.vision)}</div></div>
              <div className="p-3 rounded-xl bg-secondary/20"><div className="text-xs uppercase text-muted-foreground">Tool calling</div><div className="font-black">{String(!!b.supports?.tool_calling)}</div></div>
              <div className="p-3 rounded-xl bg-secondary/20"><div className="text-xs uppercase text-muted-foreground">Streaming</div><div className="font-black">{String(!!b.supports?.streaming)}</div></div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-card border border-border rounded-3xl overflow-hidden">
        <div className="px-6 py-4 border-b border-border font-black">Exportable Reports</div>
        <div className="divide-y divide-border">
          {reports.data?.map((r: any) => (
            <div key={r.run_id} className="px-6 py-4 flex items-center justify-between gap-4">
              <div>
                <div className="font-bold">{r.benchmark} · {r.model_name}</div>
                <div className="text-xs text-muted-foreground font-mono">{r.run_id}</div>
              </div>
              <button
                onClick={async () => {
                  const res = await api.exportAgentBenchmarkReport(r.run_id, r.benchmark, 'json')
                  navigator.clipboard.writeText(JSON.stringify(res.data, null, 2))
                  toast.success('Relatório copiado para a área de transferência.')
                }}
                className="flex items-center gap-2 text-sm font-bold text-primary"
              >
                <FileDown className="w-4 h-4" /> Export
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
