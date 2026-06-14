import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bot, Play, Shield, ShieldAlert } from 'lucide-react'
import { toast } from 'sonner'
import { AgentRiskBadge } from '../../components/agents/AgentRiskBadge'
import { AgentStatusBadge } from '../../components/agents/AgentStatusBadge'
import { JsonPanel, MetricCard, SectionCard, inputClassName } from '../../components/admin/AdminSurface'
import { LoadingCard } from '../../components/ui-feedback'
import api from '../../lib/api'

const emptyAgent = {
  name: '',
  version: '1.0.0',
  description: '',
  instructions: '',
  model_id: '',
  owner: 'admin',
  tenant_id: 'default',
  status: 'draft',
  risk_level: 'low',
}

export default function AgentRegistry() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [form, setForm] = useState<any>(emptyAgent)
  const [playbookId, setPlaybookId] = useState('')

  const agentsQuery = useQuery({ queryKey: ['admin-agents'], queryFn: () => api.listAdminAgents() })
  const budgetsQuery = useQuery({ queryKey: ['admin-agent-budgets'], queryFn: api.getAdminAgentBudgets })
  const sloClassesQuery = useQuery({ queryKey: ['admin-agent-slo-classes'], queryFn: api.getAdminAgentSloClasses })
  const playbooksQuery = useQuery({ queryKey: ['admin-agent-playbooks'], queryFn: api.listAdminAgentIncidentPlaybooks })
  const registryQuery = useQuery({ queryKey: ['agent-registry'], queryFn: api.listAgentRegistry })
  const selectedAgent = useMemo(() => (agentsQuery.data ?? []).find((agent: any) => agent.id === selectedId) ?? null, [agentsQuery.data, selectedId])
  const sloReportQuery = useQuery({
    queryKey: ['admin-agent-slo-report', selectedId],
    queryFn: () => api.getAdminAgentSloReport(selectedId || undefined),
    enabled: Boolean(selectedId),
  })

  useEffect(() => {
    if (selectedAgent) {
      setForm({
        name: selectedAgent.name || '',
        version: selectedAgent.version || '1.0.0',
        description: selectedAgent.description || '',
        instructions: selectedAgent.instructions || '',
        model_id: selectedAgent.model_id || '',
        owner: selectedAgent.owner || 'admin',
        tenant_id: selectedAgent.tenant_id || 'default',
        status: selectedAgent.status || 'draft',
        risk_level: selectedAgent.risk_level || 'low',
      })
    } else {
      setForm(emptyAgent)
    }
  }, [selectedAgent])

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (selectedId) return api.updateAdminAgent(selectedId, form)
      return api.createAdminAgent(form)
    },
    onSuccess: () => {
      toast.success('Agente salvo.')
      queryClient.invalidateQueries({ queryKey: ['admin-agents'] })
    },
    onError: (error: any) => toast.error(error.message || 'Falha ao salvar agente.'),
  })

  const statusMutation = useMutation({
    mutationFn: async (action: 'activate' | 'deprecate') => {
      if (!selectedId) throw new Error('Selecione um agente')
      return action === 'activate' ? api.activateAdminAgent(selectedId) : api.deprecateAdminAgent(selectedId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-agents'] })
      toast.success('Status atualizado.')
    },
    onError: (error: any) => toast.error(error.message || 'Falha ao atualizar status.'),
  })

  const playbookMutation = useMutation({
    mutationFn: async () => {
      if (!playbookId) throw new Error('Selecione um playbook')
      return api.runAdminAgentIncidentPlaybook(playbookId, { playbook_id: playbookId, confirmation: true, performed_by: 'admin', dry_run: true })
    },
    onSuccess: () => toast.success('Playbook executado em dry-run.'),
    onError: (error: any) => toast.error(error.message || 'Falha ao executar playbook.'),
  })

  if (agentsQuery.isLoading) return <LoadingCard />

  const activeAgents = (agentsQuery.data ?? []).filter((agent: any) => agent.status === 'active').length

  return (
    <div className="space-y-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Runtime Admin</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight text-foreground">Agent Registry</h1>
          <p className="mt-2 text-lg text-muted-foreground">CRUD operacional de agentes, SLO, budgets e incident playbooks.</p>
        </div>
        <div className="rounded-3xl bg-primary/10 p-4 text-primary">
          <Bot className="h-8 w-8" />
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Agents" value={String((agentsQuery.data ?? []).length)} />
        <MetricCard label="Active" value={String(activeAgents)} />
        <MetricCard label="Budget Classes" value={String(Object.keys(budgetsQuery.data ?? {}).length)} />
        <MetricCard label="Playbooks" value={String((playbooksQuery.data ?? []).length)} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
        <SectionCard title="Agents" subtitle="Definicoes reais do runtime administrativo.">
          <div className="space-y-3">
            {(agentsQuery.data ?? []).map((agent: any) => (
              <button
                key={agent.id}
                onClick={() => setSelectedId(agent.id)}
                className={`w-full rounded-2xl border p-4 text-left transition-colors ${selectedId === agent.id ? 'border-primary bg-primary/5' : 'border-border bg-background/70 hover:bg-muted/40'}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold text-foreground">{agent.name}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{agent.model_id}</div>
                  </div>
                  <AgentStatusBadge status={agent.status || 'unknown'} />
                </div>
                <div className="mt-3 flex items-center justify-between gap-3 text-xs text-muted-foreground">
                  <AgentRiskBadge level={agent.risk_level || 'low'} />
                  <span>{agent.version}</span>
                </div>
              </button>
            ))}
          </div>
        </SectionCard>

        <div className="space-y-6">
          <SectionCard
            title={selectedId ? 'Edit Agent' : 'Create Agent'}
            subtitle="Opera diretamente sobre /admin/agents."
            actions={
              <div className="flex gap-2">
                {selectedId && (
                  <>
                    <button onClick={() => statusMutation.mutate('activate')} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">
                      Activate
                    </button>
                    <button onClick={() => statusMutation.mutate('deprecate')} className="rounded-2xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100">
                      Deprecate
                    </button>
                  </>
                )}
                <button onClick={() => saveMutation.mutate()} className="rounded-2xl bg-foreground px-4 py-2 text-sm font-semibold text-background">
                  Save
                </button>
              </div>
            }
          >
            <div className="grid gap-3 md:grid-cols-2">
              {[
                ['name', 'Name'],
                ['version', 'Version'],
                ['model_id', 'Model ID'],
                ['owner', 'Owner'],
                ['tenant_id', 'Tenant'],
              ].map(([key, label]) => (
                <label key={key} className="grid gap-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{label}</span>
                  <input value={form[key]} onChange={event => setForm((prev: any) => ({ ...prev, [key]: event.target.value }))} className={inputClassName} />
                </label>
              ))}
              <label className="grid gap-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Status</span>
                <select value={form.status} onChange={event => setForm((prev: any) => ({ ...prev, status: event.target.value }))} className={inputClassName}>
                  <option value="draft">draft</option>
                  <option value="active">active</option>
                  <option value="deprecated">deprecated</option>
                </select>
              </label>
              <label className="grid gap-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Risk</span>
                <select value={form.risk_level} onChange={event => setForm((prev: any) => ({ ...prev, risk_level: event.target.value }))} className={inputClassName}>
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                  <option value="critical">critical</option>
                </select>
              </label>
              <label className="grid gap-2 md:col-span-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Description</span>
                <textarea value={form.description} onChange={event => setForm((prev: any) => ({ ...prev, description: event.target.value }))} className={`${inputClassName} min-h-24`} />
              </label>
              <label className="grid gap-2 md:col-span-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Instructions</span>
                <textarea value={form.instructions} onChange={event => setForm((prev: any) => ({ ...prev, instructions: event.target.value }))} className={`${inputClassName} min-h-40`} />
              </label>
            </div>
          </SectionCard>

          <div className="grid gap-6 xl:grid-cols-2">
            <SectionCard title="Budgets" subtitle="Classes e limites ativos.">
              <JsonPanel data={budgetsQuery.data} />
            </SectionCard>
            <SectionCard title="SLO" subtitle="Classes e relatorio do agente selecionado.">
              <div className="mb-4 text-xs text-muted-foreground">
                Classes: {Object.keys(sloClassesQuery.data ?? {}).length}
              </div>
              <JsonPanel data={sloReportQuery.data} empty="Selecione um agente para ver o relatorio." />
            </SectionCard>
          </div>

          <SectionCard
            title="Incident Playbooks"
            subtitle="Dry-run operacional dos playbooks cadastrados."
            actions={
              <button onClick={() => playbookMutation.mutate()} className="inline-flex items-center gap-2 rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">
                <Play className="h-4 w-4" />
                Run Dry-Run
              </button>
            }
          >
            <div className="mb-4 grid gap-2">
              <select value={playbookId} onChange={event => setPlaybookId(event.target.value)} className={inputClassName}>
                <option value="">Selecione um playbook</option>
                {(playbooksQuery.data ?? []).map((playbook: any) => (
                  <option key={playbook.id || playbook.playbook_id || playbook.name} value={playbook.id || playbook.playbook_id || playbook.name}>
                    {playbook.name || playbook.playbook_id || playbook.id}
                  </option>
                ))}
              </select>
            </div>
            <JsonPanel data={playbooksQuery.data} />
          </SectionCard>

          <SectionCard title="Registry Compat" subtitle="Comparacao com /admin/agent-registry legado.">
            <JsonPanel data={registryQuery.data} />
          </SectionCard>
        </div>
      </div>
    </div>
  )
}
