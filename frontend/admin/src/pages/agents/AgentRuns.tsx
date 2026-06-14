import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, ChevronRight, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { AgentStatusBadge } from '../../components/agents/AgentStatusBadge'
import { LoadingCard } from '../../components/ui-feedback'
import api from '../../lib/api'

const inputClassName = 'rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary'

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{label}</div>
      <div className="mt-2 text-2xl font-black text-foreground">{value}</div>
    </div>
  )
}

export default function AgentRuns() {
  const [search, setSearch] = useState('')
  const [tenantId, setTenantId] = useState('')

  const runsQuery = useQuery({
    queryKey: ['agent-runs-admin', tenantId],
    queryFn: () => api.listAdminAgentRuns(tenantId || undefined),
  })
  const clientsQuery = useQuery({
    queryKey: ['clients'],
    queryFn: api.listClients,
  })
  const registryQuery = useQuery({
    queryKey: ['agent-registry'],
    queryFn: api.listAgentRegistry,
  })

  const agentNameById = useMemo(() => {
    const entries = registryQuery.data ?? []
    return new Map(entries.map((entry: any) => [String(entry.id), entry.name || entry.slug || String(entry.id)]))
  }, [registryQuery.data])

  const runs = runsQuery.data ?? []
  const filteredRuns = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return runs
    return runs.filter((run: any) =>
      [
        run.id,
        run.agent_id,
        run.tenant_id,
        run.status,
        run.correlation_id,
        agentNameById.get(String(run.agent_id)),
      ].some(value => String(value ?? '').toLowerCase().includes(term)),
    )
  }, [agentNameById, runs, search])

  const failedRuns = filteredRuns.filter((run: any) => run.status === 'failed').length
  const activeRuns = filteredRuns.filter((run: any) => ['running', 'executing', 'pending'].includes(String(run.status))).length

  if (runsQuery.isLoading) return <LoadingCard />

  return (
    <div className="space-y-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Operational Visibility</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight text-foreground">Agent Runs</h1>
          <p className="mt-2 text-lg text-muted-foreground">Historico operacional, filtros por tenant e investigacao de execucoes reais.</p>
        </div>
        <div className="rounded-3xl bg-primary/10 p-4 text-primary">
          <Activity className="h-8 w-8" />
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Visible Runs" value={String(filteredRuns.length)} />
        <StatCard label="Active" value={String(activeRuns)} />
        <StatCard label="Failed" value={String(failedRuns)} />
      </div>

      <section className="rounded-3xl border border-border bg-card p-6 shadow-sm">
        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_280px]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={event => setSearch(event.target.value)}
              className={`${inputClassName} w-full pl-11`}
              placeholder="Buscar por run, agente, tenant ou correlation ID"
            />
          </div>

          <select value={tenantId} onChange={event => setTenantId(event.target.value)} className={inputClassName}>
            <option value="">Todos os tenants</option>
            {(clientsQuery.data ?? []).map((client: any) => (
              <option key={client.id} value={client.id}>
                {client.name || client.slug || client.id}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-6 overflow-x-auto">
          <table className="w-full min-w-[980px] text-left">
            <thead>
              <tr className="border-b border-border text-[10px] font-black uppercase tracking-[0.24em] text-muted-foreground">
                <th className="px-4 py-3">Run ID</th>
                <th className="px-4 py-3">Agent</th>
                <th className="px-4 py-3">Tenant</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Steps</th>
                <th className="px-4 py-3">Tokens</th>
                <th className="px-4 py-3">Cost</th>
                <th className="px-4 py-3">Started</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredRuns.map((run: any) => (
                <tr key={run.id} className="border-b border-border/70 text-sm last:border-0">
                  <td className="px-4 py-4 font-mono text-xs text-muted-foreground">{run.id}</td>
                  <td className="px-4 py-4 font-medium text-foreground">
                    {agentNameById.get(String(run.agent_id)) || run.agent_id}
                  </td>
                  <td className="px-4 py-4 text-muted-foreground">{run.tenant_id}</td>
                  <td className="px-4 py-4"><AgentStatusBadge status={run.status || 'unknown'} /></td>
                  <td className="px-4 py-4 text-muted-foreground">{run.total_steps ?? 0}</td>
                  <td className="px-4 py-4 text-muted-foreground">{run.total_tokens ?? 0}</td>
                  <td className="px-4 py-4 text-muted-foreground">
                    {typeof run.estimated_cost_brl === 'number' ? `R$ ${run.estimated_cost_brl.toFixed(2)}` : 'R$ 0.00'}
                  </td>
                  <td className="px-4 py-4 text-muted-foreground">{run.started_at ? new Date(run.started_at).toLocaleString() : 'N/A'}</td>
                  <td className="px-4 py-4 text-right">
                    <Link
                      to={`/agents/runs/${run.id}`}
                      className="inline-flex items-center gap-2 rounded-2xl border border-border px-3 py-2 text-xs font-semibold text-foreground transition-colors hover:bg-muted"
                    >
                      Inspect
                      <ChevronRight className="h-4 w-4" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {!filteredRuns.length && (
            <div className="rounded-2xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
              Nenhum run encontrado para os filtros atuais.
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
