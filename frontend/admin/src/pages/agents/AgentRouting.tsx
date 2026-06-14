import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Network, Play } from 'lucide-react'
import { toast } from 'sonner'
import { JsonPanel, MetricCard, SectionCard, inputClassName } from '../../components/admin/AdminSurface'
import { LoadingCard } from '../../components/ui-feedback'
import api from '../../lib/api'

export default function AgentRouting() {
  const [stepType, setStepType] = useState('tool_call')
  const [inputText, setInputText] = useState('')
  const [policyName, setPolicyName] = useState('balanced')
  const [runId, setRunId] = useState('')

  const capabilitiesQuery = useQuery({ queryKey: ['agent-routing-capabilities'], queryFn: api.listAgentRoutingCapabilities })
  const decisionsQuery = useQuery({ queryKey: ['agent-routing-decisions', runId], queryFn: () => api.listAgentRoutingDecisions(runId || undefined) })
  const simulateMutation = useMutation({
    mutationFn: () => api.simulateAgentRouting({ step_type: stepType, input_text: inputText, policy_name: policyName }),
    onError: (error: any) => toast.error(error.message || 'Falha na simulacao.'),
  })

  if (capabilitiesQuery.isLoading) return <LoadingCard />

  return (
    <div className="space-y-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Model Routing</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight text-foreground">Agent Routing</h1>
          <p className="mt-2 text-lg text-muted-foreground">Capabilities, simulacao de decisao e historico de roteamento por step.</p>
        </div>
        <div className="rounded-3xl bg-primary/10 p-4 text-primary">
          <Network className="h-8 w-8" />
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Capabilities" value={String((capabilitiesQuery.data ?? []).length)} />
        <MetricCard label="Decisions" value={String((decisionsQuery.data ?? []).length)} />
        <MetricCard label="Policy" value={policyName} />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard
          title="Simulate"
          subtitle="POST /admin/agents/routing/simulate"
          actions={
            <button onClick={() => simulateMutation.mutate()} className="inline-flex items-center gap-2 rounded-2xl bg-foreground px-4 py-2 text-sm font-semibold text-background">
              <Play className="h-4 w-4" />
              Simulate
            </button>
          }
        >
          <div className="grid gap-3">
            <input value={stepType} onChange={event => setStepType(event.target.value)} className={inputClassName} placeholder="tool_call" />
            <input value={policyName} onChange={event => setPolicyName(event.target.value)} className={inputClassName} placeholder="balanced" />
            <textarea value={inputText} onChange={event => setInputText(event.target.value)} className={`${inputClassName} min-h-32`} placeholder="Texto de entrada para roteamento" />
          </div>
          <div className="mt-4">
            <JsonPanel data={simulateMutation.data} empty="Execute uma simulacao para ver a decisao." />
          </div>
        </SectionCard>

        <SectionCard title="Capabilities" subtitle="Catalogo atual de modelos e classes de latencia.">
          <JsonPanel data={capabilitiesQuery.data} />
        </SectionCard>
      </div>

      <SectionCard title="Recent Decisions" subtitle="Consulta opcional por run_id.">
        <div className="mb-4">
          <input value={runId} onChange={event => setRunId(event.target.value)} className={inputClassName} placeholder="Filtrar por run_id opcional" />
        </div>
        <JsonPanel data={decisionsQuery.data} />
      </SectionCard>
    </div>
  )
}
