import { useEffect, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, Play, RefreshCw, ShieldAlert, Wrench } from 'lucide-react'
import { toast } from 'sonner'

import api from '../../lib/api'

export default function AgentTools() {
  const queryClient = useQueryClient()
  const [tenantId, setTenantId] = useState('default')
  const [selectedToolId, setSelectedToolId] = useState('')
  const [executionParams, setExecutionParams] = useState('{\n  "sample": true\n}')

  const { data: clients = [] } = useQuery({
    queryKey: ['tool-clients'],
    queryFn: () => api.listClients(),
  })

  useEffect(() => {
    if (tenantId === 'default' && Array.isArray(clients) && clients[0]?.id) {
      setTenantId(clients[0].id)
    }
  }, [clients, tenantId])

  const { data: tools = [] } = useQuery({
    queryKey: ['agent-tools-admin'],
    queryFn: () => api.listAgentToolsAdmin(),
  })

  const { data: sideEffects = [] } = useQuery({
    queryKey: ['agent-tool-side-effects', tenantId],
    queryFn: () => api.listAgentToolSideEffects(tenantId),
    enabled: !!tenantId,
  })

  const { data: credentials = [] } = useQuery({
    queryKey: ['agent-tool-credentials', tenantId],
    queryFn: () => api.listAgentToolCredentials(tenantId),
    enabled: !!tenantId,
  })

  const { data: quotas = [] } = useQuery({
    queryKey: ['agent-tool-quotas', tenantId],
    queryFn: () => api.listAgentToolQuotas(tenantId),
    enabled: !!tenantId,
  })

  const { data: invocations = [] } = useQuery({
    queryKey: ['agent-tool-invocations', selectedToolId],
    queryFn: () => api.listAgentToolInvocations(selectedToolId),
    enabled: !!selectedToolId,
  })

  const dryRunMutation = useMutation({
    mutationFn: () => api.dryRunAgentTool(selectedToolId, parseJson(executionParams), tenantId),
    onSuccess: () => {
      toast.success('Dry-run executado.')
      refreshTools(queryClient)
    },
    onError: (error: any) => toast.error(error?.message || 'Falha no dry-run'),
  })

  const executeMutation = useMutation({
    mutationFn: () => api.executeAgentToolAdmin(selectedToolId, parseJson(executionParams), tenantId),
    onSuccess: () => {
      toast.success('Execucao real concluida.')
      refreshTools(queryClient)
    },
    onError: (error: any) => toast.error(error?.message || 'Falha na execucao'),
  })

  const selectedTool = tools.find((tool: any) => tool.id === selectedToolId) || null

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">Agent Tools</h1>
          <p className="text-sm md:text-lg text-muted-foreground">Catalogo real de ferramentas, quotas, credenciais, side effects e invocacoes.</p>
        </div>
        <button type="button" onClick={() => refreshTools(queryClient)} className="rounded-xl border border-border px-4 py-2.5 text-sm font-bold hover:bg-secondary">
          <RefreshCw className="mr-2 inline h-4 w-4" />
          Atualizar
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2">
          <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Tenant</span>
          <select value={tenantId} onChange={e => setTenantId(e.target.value)} className={inputClassName}>
            {Array.isArray(clients) && clients.map((client: any) => (
              <option key={client.id} value={client.id}>{client.name || client.id}</option>
            ))}
            {!Array.isArray(clients) || clients.length === 0 ? <option value="default">default</option> : null}
          </select>
        </label>
        <label className="space-y-2">
          <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Tool</span>
          <select value={selectedToolId} onChange={e => setSelectedToolId(e.target.value)} className={inputClassName}>
            <option value="">Selecione uma ferramenta</option>
            {tools.map((tool: any) => (
              <option key={tool.id} value={tool.id}>{tool.name} ({tool.version})</option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Ferramentas" value={String(tools.length)} icon={<Wrench className="h-5 w-5" />} />
        <MetricCard label="Credentials" value={String(credentials.length)} icon={<KeyRound className="h-5 w-5 text-primary" />} />
        <MetricCard label="Side Effects" value={String(sideEffects.length)} icon={<ShieldAlert className="h-5 w-5 text-destructive" />} />
        <MetricCard label="Quotas" value={String(quotas.length)} icon={<RefreshCw className="h-5 w-5" />} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <Card title="Catalogo de Ferramentas">
          <div className="space-y-3">
            {tools.length ? tools.map((tool: any) => (
              <button
                key={tool.id}
                type="button"
                onClick={() => setSelectedToolId(tool.id)}
                className={`w-full rounded-2xl border p-4 text-left transition-all ${
                  selectedToolId === tool.id ? 'border-primary bg-primary/5' : 'border-border bg-background hover:bg-secondary/40'
                }`}
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-bold text-foreground">{tool.name}</div>
                    <div className="text-xs text-muted-foreground">{tool.category} · v{tool.version}</div>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-widest ${
                    tool.enabled ? 'bg-emerald-500/10 text-emerald-600' : 'bg-secondary text-muted-foreground'
                  }`}>
                    {tool.enabled ? 'enabled' : 'disabled'}
                  </span>
                </div>
                <div className="mt-3 text-sm text-muted-foreground">{tool.description || 'Sem descricao.'}</div>
              </button>
            )) : (
              <div className="rounded-2xl border border-dashed border-border p-6 text-sm text-muted-foreground">Nenhuma ferramenta registrada.</div>
            )}
          </div>
        </Card>

        <Card title={selectedTool ? `Execucao: ${selectedTool.name}` : 'Execucao'}>
          {selectedTool ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <DetailCard label="Risk" value={selectedTool.risk_level} />
                <DetailCard label="Side effect" value={selectedTool.side_effect_level} />
                <DetailCard label="Approval" value={selectedTool.requires_approval ? 'sim' : 'nao'} />
                <DetailCard label="Dry-run" value={selectedTool.dry_run_supported ? 'sim' : 'nao'} />
              </div>
              <label className="space-y-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Parametros JSON</span>
                <textarea value={executionParams} onChange={e => setExecutionParams(e.target.value)} className={`${inputClassName} min-h-[180px] font-mono text-xs`} />
              </label>
              <div className="flex gap-3">
                <button type="button" onClick={() => dryRunMutation.mutate()} className="rounded-xl border border-border px-4 py-2.5 text-sm font-bold hover:bg-secondary">
                  Dry-run
                </button>
                <button type="button" onClick={() => executeMutation.mutate()} className="rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:bg-primary/90">
                  <Play className="mr-2 inline h-4 w-4" />
                  Executar
                </button>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-border p-6 text-sm text-muted-foreground">Selecione uma ferramenta para operar.</div>
          )}
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Invocations">
          <JsonList values={invocations} />
        </Card>
        <Card title="Side Effects">
          <JsonList values={sideEffects} />
        </Card>
        <Card title="Credentials">
          <JsonList values={credentials} />
        </Card>
        <Card title="Quotas">
          <JsonList values={quotas} />
        </Card>
      </div>
    </div>
  )
}

function refreshTools(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ['agent-tools-admin'] })
  queryClient.invalidateQueries({ queryKey: ['agent-tool-invocations'] })
  queryClient.invalidateQueries({ queryKey: ['agent-tool-side-effects'] })
  queryClient.invalidateQueries({ queryKey: ['agent-tool-credentials'] })
  queryClient.invalidateQueries({ queryKey: ['agent-tool-quotas'] })
}

function parseJson(raw: string) {
  try {
    return JSON.parse(raw)
  } catch {
    throw new Error('Parametros JSON invalidos')
  }
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

function DetailCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border bg-background p-3">
      <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm font-semibold text-foreground">{value}</div>
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

const inputClassName = 'w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary'
