import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { GitBranch, Play } from 'lucide-react'
import { toast } from 'sonner'
import { JsonPanel, SectionCard, inputClassName } from '../../components/admin/AdminSurface'
import api from '../../lib/api'

export default function AgentWorkflowOps() {
  const [workflowName, setWorkflowName] = useState('')
  const [workflowVersion, setWorkflowVersion] = useState('1.0.0')
  const [tenantId, setTenantId] = useState('default')
  const [workflowId, setWorkflowId] = useState('')
  const [runId, setRunId] = useState('')
  const [signalName, setSignalName] = useState('continue')

  const createMutation = useMutation({
    mutationFn: () => api.createAgentWorkflow({ name: workflowName, version: workflowVersion, tenant_id: tenantId, input_data: {} }),
    onSuccess: () => toast.success('Workflow criado.'),
    onError: (error: any) => toast.error(error.message || 'Falha ao criar workflow.'),
  })
  const runMutation = useMutation({
    mutationFn: () => api.runAgentWorkflow(workflowId, { tenant_id: tenantId, input_data: {} }),
    onSuccess: (data: any) => {
      if (data?.id) setRunId(data.id)
      toast.success('Workflow run criado.')
    },
    onError: (error: any) => toast.error(error.message || 'Falha ao iniciar workflow.'),
  })
  const detailMutation = useMutation({ mutationFn: () => api.getAgentWorkflowRun(workflowId, runId) })
  const signalMutation = useMutation({ mutationFn: () => api.signalAgentWorkflow(workflowId, runId, { signal_name: signalName, payload: {} }) })
  const cancelMutation = useMutation({ mutationFn: () => api.cancelAgentWorkflow(workflowId, runId) })
  const webhookMutation = useMutation({ mutationFn: () => api.createAgentWorkflowWebhookWait(workflowId, runId) })
  const pollingMutation = useMutation({ mutationFn: () => api.createAgentWorkflowPollingJob(workflowId, runId, { url: 'https://example.com', stop_condition: { status: 'done' }, interval: 60 }) })
  const eventsMutation = useMutation({ mutationFn: () => api.listAgentWorkflowExternalEvents(workflowId, runId) })

  return (
    <div className="space-y-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Workflow Runtime</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight text-foreground">Agent Workflows</h1>
          <p className="mt-2 text-lg text-muted-foreground">CRUD e operacao da superficie de workflows agentic.</p>
        </div>
        <div className="rounded-3xl bg-primary/10 p-4 text-primary">
          <GitBranch className="h-8 w-8" />
        </div>
      </header>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Create Workflow" subtitle="POST /admin/agents/workflows">
          <div className="grid gap-3">
            <input value={workflowName} onChange={event => setWorkflowName(event.target.value)} className={inputClassName} placeholder="Workflow name" />
            <input value={workflowVersion} onChange={event => setWorkflowVersion(event.target.value)} className={inputClassName} placeholder="1.0.0" />
            <input value={tenantId} onChange={event => setTenantId(event.target.value)} className={inputClassName} placeholder="default" />
            <button onClick={() => createMutation.mutate()} className="rounded-2xl bg-foreground px-4 py-2 text-sm font-semibold text-background">Create</button>
          </div>
        </SectionCard>

        <SectionCard title="Run Workflow" subtitle="POST /admin/agents/workflows/{id}/run">
          <div className="grid gap-3">
            <input value={workflowId} onChange={event => setWorkflowId(event.target.value)} className={inputClassName} placeholder="workflow_id" />
            <input value={tenantId} onChange={event => setTenantId(event.target.value)} className={inputClassName} placeholder="tenant_id" />
            <button onClick={() => runMutation.mutate()} className="inline-flex items-center gap-2 rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">
              <Play className="h-4 w-4" />
              Run
            </button>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Run Controls" subtitle="Signal, cancel, webhook wait, polling e external events.">
        <div className="grid gap-3 md:grid-cols-3">
          <input value={workflowId} onChange={event => setWorkflowId(event.target.value)} className={inputClassName} placeholder="workflow_id" />
          <input value={runId} onChange={event => setRunId(event.target.value)} className={inputClassName} placeholder="run_id" />
          <input value={signalName} onChange={event => setSignalName(event.target.value)} className={inputClassName} placeholder="signal_name" />
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <button onClick={() => detailMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Get Run</button>
          <button onClick={() => signalMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Signal</button>
          <button onClick={() => cancelMutation.mutate()} className="rounded-2xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100">Cancel</button>
          <button onClick={() => webhookMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Webhook Wait</button>
          <button onClick={() => pollingMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Polling Job</button>
          <button onClick={() => eventsMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">External Events</button>
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Latest Run Response" subtitle="Resultado mais recente de operacao.">
          <JsonPanel data={eventsMutation.data ?? pollingMutation.data ?? webhookMutation.data ?? cancelMutation.data ?? signalMutation.data ?? detailMutation.data ?? runMutation.data ?? createMutation.data} />
        </SectionCard>
      </div>
    </div>
  )
}
