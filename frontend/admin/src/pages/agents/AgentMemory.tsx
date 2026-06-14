import { useEffect, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Database, Download, FileSearch, RefreshCw, ShieldCheck, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import api from '../../lib/api'

export default function AgentMemory() {
  const queryClient = useQueryClient()
  const [tenantId, setTenantId] = useState('default')
  const [agentId, setAgentId] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])

  const { data: clients = [] } = useQuery({
    queryKey: ['memory-clients'],
    queryFn: () => api.listClients(),
  })

  useEffect(() => {
    if (tenantId === 'default' && Array.isArray(clients) && clients[0]?.id) {
      setTenantId(clients[0].id)
    }
  }, [clients, tenantId])

  const { data: items = [] } = useQuery({
    queryKey: ['agent-memory-items', tenantId, agentId],
    queryFn: () => api.listAgentMemoryItems(tenantId, agentId || undefined),
    enabled: !!tenantId,
  })

  const { data: accessEvents = [] } = useQuery({
    queryKey: ['agent-memory-access-events', tenantId, agentId],
    queryFn: () => api.listAgentMemoryAccessEvents(tenantId, agentId || undefined),
    enabled: !!tenantId,
  })

  const { data: policies = [] } = useQuery({
    queryKey: ['agent-memory-policies', tenantId],
    queryFn: () => api.listAgentMemoryPolicies(tenantId),
    enabled: !!tenantId,
  })

  const { data: consents = [] } = useQuery({
    queryKey: ['agent-memory-consents', tenantId],
    queryFn: () => api.listAgentMemoryConsents(tenantId),
    enabled: !!tenantId,
  })

  const retentionMutation = useMutation({
    mutationFn: () => api.runAgentMemoryRetention(),
    onSuccess: () => {
      toast.success('Retencao executada com sucesso.')
      refreshMemory(queryClient)
    },
    onError: (error: any) => toast.error(error?.message || 'Falha ao executar retencao'),
  })

  const exportMutation = useMutation({
    mutationFn: () => api.exportAgentMemory({ tenant_id: tenantId, agent_id: agentId || null }),
    onSuccess: (result: any[]) => {
      const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `agent-memory-${tenantId}.json`
      a.click()
      toast.success('Export concluido.')
    },
    onError: (error: any) => toast.error(error?.message || 'Falha ao exportar memoria'),
  })

  const deleteRequestMutation = useMutation({
    mutationFn: () => api.createAgentMemoryDeleteRequest({ tenant_id: tenantId, agent_id: agentId || null }),
    onSuccess: () => toast.success('Delete request registrada.'),
    onError: (error: any) => toast.error(error?.message || 'Falha ao criar delete request'),
  })

  const deleteItemMutation = useMutation({
    mutationFn: (itemId: string) => api.deleteAgentMemoryItem(itemId, tenantId),
    onSuccess: () => {
      toast.success('Item removido.')
      refreshMemory(queryClient)
    },
    onError: (error: any) => toast.error(error?.message || 'Falha ao remover item'),
  })

  const searchMutation = useMutation({
    mutationFn: () => api.searchAgentMemory({ tenant_id: tenantId, agent_id: agentId, query: searchQuery, limit: 20 }),
    onSuccess: result => setSearchResults(result),
    onError: (error: any) => toast.error(error?.message || 'Falha na busca de memoria'),
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">Agent Memory</h1>
          <p className="text-sm md:text-lg text-muted-foreground">Superficie real para itens, politicas, consentimentos e trilhas de acesso.</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <button type="button" onClick={() => exportMutation.mutate()} className="rounded-xl border border-border px-4 py-2.5 text-sm font-bold hover:bg-secondary">
            <Download className="mr-2 inline h-4 w-4" />
            Exportar
          </button>
          <button type="button" onClick={() => retentionMutation.mutate()} className="rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:bg-primary/90">
            <RefreshCw className="mr-2 inline h-4 w-4" />
            Run Retention
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <FilterField label="Tenant">
          <select value={tenantId} onChange={e => setTenantId(e.target.value)} className={inputClassName}>
            {Array.isArray(clients) && clients.map((client: any) => (
              <option key={client.id} value={client.id}>{client.name || client.id}</option>
            ))}
            {!Array.isArray(clients) || clients.length === 0 ? <option value="default">default</option> : null}
          </select>
        </FilterField>
        <FilterField label="Agent ID">
          <input value={agentId} onChange={e => setAgentId(e.target.value)} className={inputClassName} placeholder="Opcional" />
        </FilterField>
        <FilterField label="Search">
          <div className="flex gap-2">
            <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} className={inputClassName} placeholder="Buscar conteudo..." />
            <button type="button" onClick={() => searchMutation.mutate()} disabled={!tenantId || !agentId || !searchQuery.trim()} className="rounded-xl border border-border px-4 text-sm font-bold hover:bg-secondary disabled:opacity-50">
              <FileSearch className="h-4 w-4" />
            </button>
          </div>
        </FilterField>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Itens" value={String(items.length)} icon={<Database className="h-5 w-5" />} />
        <MetricCard label="Access Events" value={String(accessEvents.length)} icon={<ShieldCheck className="h-5 w-5 text-primary" />} />
        <MetricCard label="Policies" value={String(policies.length)} icon={<RefreshCw className="h-5 w-5" />} />
        <MetricCard label="Consents" value={String(consents.length)} icon={<Download className="h-5 w-5" />} />
      </div>

      {searchResults.length > 0 && (
        <Card title="Search Results">
          <JsonList values={searchResults} />
        </Card>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Memory Items">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs font-black uppercase tracking-widest text-muted-foreground">
                <th className="py-3 pr-4">ID</th>
                <th className="py-3 pr-4">Type</th>
                <th className="py-3 pr-4">Summary</th>
                <th className="py-3 pr-4">Created</th>
                <th className="py-3 pr-4"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((item: any) => (
                <tr key={item.id}>
                  <td className="py-3 pr-4 font-mono text-xs text-muted-foreground">{String(item.id).slice(0, 12)}</td>
                  <td className="py-3 pr-4 text-foreground">{item.memory_type}</td>
                  <td className="py-3 pr-4 text-foreground">{item.summary || '-'}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{new Date(item.created_at).toLocaleString()}</td>
                  <td className="py-3 pr-4">
                    <button type="button" onClick={() => deleteItemMutation.mutate(item.id)} className="rounded-lg p-2 text-destructive hover:bg-destructive/10">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {!items.length && (
                <tr><td colSpan={5} className="py-8 text-center text-muted-foreground">Nenhum item encontrado.</td></tr>
              )}
            </tbody>
          </table>
        </Card>

        <Card title="Access Events">
          <JsonList values={accessEvents} />
        </Card>

        <Card title="Policies">
          <JsonList values={policies} />
        </Card>

        <Card title="Consents">
          <div className="space-y-4">
            <JsonList values={consents} />
            <div className="flex justify-end gap-3 border-t border-border pt-4">
              <button type="button" onClick={() => deleteRequestMutation.mutate()} className="rounded-xl border border-border px-4 py-2 text-sm font-bold hover:bg-secondary">
                Criar Delete Request
              </button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

function refreshMemory(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ['agent-memory-items'] })
  queryClient.invalidateQueries({ queryKey: ['agent-memory-access-events'] })
  queryClient.invalidateQueries({ queryKey: ['agent-memory-policies'] })
  queryClient.invalidateQueries({ queryKey: ['agent-memory-consents'] })
}

function FilterField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="space-y-2">
      <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">{label}</span>
      {children}
    </label>
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
