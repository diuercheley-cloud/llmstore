import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { GitBranch, Play } from 'lucide-react'
import { toast } from 'sonner'
import { JsonPanel, MetricCard, SectionCard, inputClassName } from '../../components/admin/AdminSurface'
import { LoadingCard } from '../../components/ui-feedback'
import api from '../../lib/api'

export default function WorkflowGovernance() {
  const [executionId, setExecutionId] = useState('')
  const [definitionName, setDefinitionName] = useState('')
  const [definitionId, setDefinitionId] = useState('')

  const statusQuery = useQuery({ queryKey: ['workflow-governance-status'], queryFn: () => api.getWorkflowGovernanceStatus() })
  const definitionsQuery = useQuery({ queryKey: ['workflow-definitions'], queryFn: () => api.listWorkflowDefinitions() })
  const executionsQuery = useQuery({ queryKey: ['workflow-executions'], queryFn: () => api.listWorkflowExecutions() })
  const reportsQuery = useQuery({ queryKey: ['workflow-reports'], queryFn: () => api.listWorkflowReports() })
  const approvalsQuery = useQuery({ queryKey: ['workflow-approvals'], queryFn: () => api.listWorkflowApprovals() })
  const replaysQuery = useQuery({ queryKey: ['workflow-replays'], queryFn: () => api.listWorkflowReplays() })
  const replaySessionsQuery = useQuery({ queryKey: ['workflow-replay-sessions'], queryFn: () => api.listWorkflowReplaySessions() })

  const createDefinitionMutation = useMutation({
    mutationFn: () => api.createWorkflowDefinition({ workflow_name: definitionName, steps_config: [], workflow_family: 'admin' }),
    onSuccess: () => definitionsQuery.refetch(),
    onError: (error: any) => toast.error(error.message || 'Falha ao criar definicao.'),
  })
  const createExecutionMutation = useMutation({
    mutationFn: () => api.createWorkflowExecution({ definition_id: definitionId, session_id: `admin-${Date.now()}`, tenant_id: 'default' }),
    onSuccess: (data: any) => {
      if (data?.id) setExecutionId(data.id)
      executionsQuery.refetch()
    },
    onError: (error: any) => toast.error(error.message || 'Falha ao criar execucao.'),
  })
  const inspectMutation = useMutation({ mutationFn: () => api.getWorkflowExecution(executionId) })
  const governanceMutation = useMutation({ mutationFn: () => api.getWorkflowGovernanceExecution(executionId) })
  const ledgerMutation = useMutation({ mutationFn: () => api.getWorkflowGovernanceLedger(executionId) })
  const snapshotsMutation = useMutation({ mutationFn: () => api.getWorkflowGovernanceSnapshots(executionId) })
  const checkpointsMutation = useMutation({ mutationFn: () => api.listWorkflowCheckpoints(executionId) })
  const replayMutation = useMutation({ mutationFn: () => api.createWorkflowReplay(executionId) })

  if (statusQuery.isLoading) return <LoadingCard />

  return (
    <div className="space-y-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Deterministic Orchestration</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight text-foreground">Workflow Governance</h1>
          <p className="mt-2 text-lg text-muted-foreground">Definitions, executions, governance ledger, approvals e replay de workflows comerciais.</p>
        </div>
        <div className="rounded-3xl bg-primary/10 p-4 text-primary">
          <GitBranch className="h-8 w-8" />
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-5">
        <MetricCard label="Definitions" value={String((definitionsQuery.data as any)?.items?.length ?? 0)} />
        <MetricCard label="Executions" value={String((executionsQuery.data as any)?.items?.length ?? 0)} />
        <MetricCard label="Approvals" value={String((approvalsQuery.data as any)?.items?.length ?? 0)} />
        <MetricCard label="Replays" value={String((replaysQuery.data as any)?.items?.length ?? 0)} />
        <MetricCard label="Reports" value={String((reportsQuery.data as any)?.items?.length ?? 0)} />
      </div>

      <SectionCard title="Status" subtitle="Resumo do motor deterministico.">
        <JsonPanel data={statusQuery.data} />
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Create Definition" subtitle="POST /admin/workflows/definitions">
          <div className="grid gap-3">
            <input value={definitionName} onChange={event => setDefinitionName(event.target.value)} className={inputClassName} placeholder="workflow_name" />
            <button onClick={() => createDefinitionMutation.mutate()} className="rounded-2xl bg-foreground px-4 py-2 text-sm font-semibold text-background">Create Definition</button>
          </div>
        </SectionCard>
        <SectionCard title="Create Execution" subtitle="POST /admin/workflows/executions">
          <div className="grid gap-3">
            <input value={definitionId} onChange={event => setDefinitionId(event.target.value)} className={inputClassName} placeholder="definition_id" />
            <button onClick={() => createExecutionMutation.mutate()} className="inline-flex items-center gap-2 rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">
              <Play className="h-4 w-4" />
              Create Execution
            </button>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Inspect Execution" subtitle="Governance, ledger, snapshots, checkpoints e replay.">
        <div className="grid gap-3 md:grid-cols-2">
          <input value={executionId} onChange={event => setExecutionId(event.target.value)} className={inputClassName} placeholder="execution_id" />
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <button onClick={() => inspectMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Execution</button>
          <button onClick={() => governanceMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Governance</button>
          <button onClick={() => ledgerMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Ledger</button>
          <button onClick={() => snapshotsMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Snapshots</button>
          <button onClick={() => checkpointsMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Checkpoints</button>
          <button onClick={() => replayMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Create Replay</button>
        </div>
        <div className="mt-4">
          <JsonPanel data={checkpointsMutation.data ?? snapshotsMutation.data ?? ledgerMutation.data ?? governanceMutation.data ?? inspectMutation.data ?? replayMutation.data} empty="Selecione uma acao para inspecionar a execucao." />
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Definitions" subtitle="Catalogo de DAGs e steps."><JsonPanel data={definitionsQuery.data} /></SectionCard>
        <SectionCard title="Executions" subtitle="Historico das execucoes."><JsonPanel data={executionsQuery.data} /></SectionCard>
        <SectionCard title="Approvals" subtitle="Corrente de aprovacao por stage."><JsonPanel data={approvalsQuery.data} /></SectionCard>
        <SectionCard title="Replay Sessions" subtitle="Comparacao e determinismo."><JsonPanel data={replaySessionsQuery.data} /></SectionCard>
        <SectionCard title="Replays" subtitle="Replays cadastrados."><JsonPanel data={replaysQuery.data} /></SectionCard>
        <SectionCard title="Reports" subtitle="Relatorios de determinismo e drift."><JsonPanel data={reportsQuery.data} /></SectionCard>
      </div>
    </div>
  )
}
