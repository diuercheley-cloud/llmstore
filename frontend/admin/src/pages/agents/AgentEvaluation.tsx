import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { BarChart3, Database, PlayCircle } from 'lucide-react'
import { toast } from 'sonner'
import { JsonPanel, MetricCard, SectionCard, inputClassName } from '../../components/admin/AdminSurface'
import { LoadingCard } from '../../components/ui-feedback'
import api from '../../lib/api'

export default function AgentEvaluation() {
  const [agentId, setAgentId] = useState('')
  const [datasetId, setDatasetId] = useState('')
  const [datasetName, setDatasetName] = useState('')
  const [datasetVersion, setDatasetVersion] = useState('v1')
  const [modelName, setModelName] = useState('llama-3-70b')

  const agentsQuery = useQuery({ queryKey: ['admin-agents'], queryFn: () => api.listAdminAgents() })
  const benchmarksQuery = useQuery({ queryKey: ['agent-evaluation-benchmarks'], queryFn: () => api.listAgentBenchmarks() })
  const reportsQuery = useQuery({ queryKey: ['agent-evaluation-reports'], queryFn: () => api.listAgentBenchmarkReports() })
  const evalReportQuery = useQuery({
    queryKey: ['agent-eval-report-admin', agentId],
    queryFn: () => api.getAgentEvalReportAdmin(agentId),
    enabled: Boolean(agentId),
  })

  const createDatasetMutation = useMutation({
    mutationFn: () => api.createAgentEvalDataset({ agent_id: agentId, name: datasetName, description: `Dataset ${datasetName}` }),
    onSuccess: (data) => {
      setDatasetId(data.id)
      toast.success('Dataset criado.')
    },
    onError: (error: any) => toast.error(error.message || 'Falha ao criar dataset.'),
  })

  const createVersionMutation = useMutation({
    mutationFn: () =>
      api.createAgentEvalDatasetVersion(datasetId, {
        version: datasetVersion,
        cases_json: [{ input: 'ping', expected: 'pong' }],
      }),
    onSuccess: () => toast.success('Versao de dataset criada.'),
    onError: (error: any) => toast.error(error.message || 'Falha ao criar versao.'),
  })

  const runMutation = useMutation({
    mutationFn: () => api.runAgentEvalAdmin({ agent_id: agentId, dataset_id: datasetId, version: datasetVersion, metadata: { source: 'admin-dashboard' } }),
    onSuccess: () => {
      toast.success('Avaliacao iniciada.')
      reportsQuery.refetch()
      evalReportQuery.refetch()
    },
    onError: (error: any) => toast.error(error.message || 'Falha ao rodar avaliacao.'),
  })

  const benchmarkMutation = useMutation({
    mutationFn: (benchmark: string) => api.runAgentBenchmark({ agent_id: agentId, model_name: modelName, benchmark }),
    onSuccess: () => {
      toast.success('Benchmark iniciado.')
      reportsQuery.refetch()
    },
    onError: (error: any) => toast.error(error.message || 'Falha ao iniciar benchmark.'),
  })

  const latestReport = useMemo(() => (reportsQuery.data ?? [])[0], [reportsQuery.data])
  const promotionGateMutation = useMutation({
    mutationFn: () => {
      const evalRunId = latestReport?.id || latestReport?.run_id
      if (!evalRunId) throw new Error('Nenhum eval run disponivel')
      return api.checkAgentPromotionGateAdmin(agentId, { eval_run_id: evalRunId, audit_override: false })
    },
    onSuccess: () => evalReportQuery.refetch(),
    onError: (error: any) => toast.error(error.message || 'Falha no promotion gate.'),
  })

  if (agentsQuery.isLoading) return <LoadingCard />

  return (
    <div className="space-y-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Evaluation Admin</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight text-foreground">Agent Evaluation</h1>
          <p className="mt-2 text-lg text-muted-foreground">Datasets versionados, runs reais, reports por agente e promotion gate.</p>
        </div>
        <div className="rounded-3xl bg-primary/10 p-4 text-primary">
          <BarChart3 className="h-8 w-8" />
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Benchmarks" value={String((benchmarksQuery.data ?? []).length)} />
        <MetricCard label="Reports" value={String((reportsQuery.data ?? []).length)} />
        <MetricCard label="Selected Agent" value={agentId ? '1' : '0'} />
        <MetricCard label="Dataset Ready" value={datasetId ? 'yes' : 'no'} />
      </div>

      <SectionCard title="Run Evaluation" subtitle="Controle real sobre datasets e suites.">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <select value={agentId} onChange={event => setAgentId(event.target.value)} className={inputClassName}>
            <option value="">Selecione um agente</option>
            {(agentsQuery.data ?? []).map((agent: any) => (
              <option key={agent.id} value={agent.id}>{agent.name}</option>
            ))}
          </select>
          <input value={datasetName} onChange={event => setDatasetName(event.target.value)} className={inputClassName} placeholder="Nome do dataset" />
          <input value={datasetVersion} onChange={event => setDatasetVersion(event.target.value)} className={inputClassName} placeholder="v1" />
          <input value={modelName} onChange={event => setModelName(event.target.value)} className={inputClassName} placeholder="Model name" />
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <button onClick={() => createDatasetMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Create Dataset</button>
          <button onClick={() => createVersionMutation.mutate()} disabled={!datasetId} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-50">Create Version</button>
          <button onClick={() => runMutation.mutate()} disabled={!agentId || !datasetId} className="inline-flex items-center gap-2 rounded-2xl bg-foreground px-4 py-2 text-sm font-semibold text-background disabled:opacity-50">
            <PlayCircle className="h-4 w-4" />
            Run Eval
          </button>
          <button onClick={() => promotionGateMutation.mutate()} disabled={!agentId} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-50">
            Promotion Gate
          </button>
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Benchmark Catalog" subtitle="Catalogo do framework atual.">
          <div className="mb-4 flex flex-wrap gap-2">
            {(benchmarksQuery.data ?? []).map((benchmark: any) => (
              <button
                key={benchmark.name}
                onClick={() => benchmarkMutation.mutate(benchmark.name)}
                disabled={!agentId}
                className="inline-flex items-center gap-2 rounded-2xl border border-border px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-50"
              >
                <Database className="h-4 w-4" />
                {benchmark.name}
              </button>
            ))}
          </div>
          <JsonPanel data={benchmarksQuery.data} />
        </SectionCard>

        <SectionCard title="Agent Eval Report" subtitle="Saida do backend de /admin/agent-evals/reports/{agent_id}.">
          <JsonPanel data={evalReportQuery.data} empty="Selecione um agente para ver o report." />
        </SectionCard>
      </div>

      <SectionCard title="Legacy Benchmark Reports" subtitle="Compatibilidade com o framework anterior ainda exposto na UI.">
        <JsonPanel data={reportsQuery.data} />
      </SectionCard>
    </div>
  )
}
