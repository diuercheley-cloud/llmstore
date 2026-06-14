import { useEffect, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Network, Play, Server, ShieldCheck, Users } from 'lucide-react'
import { toast } from 'sonner'

import api from '../../lib/api'

export default function AgentProtocols() {
  const queryClient = useQueryClient()
  const [tenantId, setTenantId] = useState('default')
  const [peerUrl, setPeerUrl] = useState('')
  const [trustProtocol, setTrustProtocol] = useState('mcp')
  const [trustEntityId, setTrustEntityId] = useState('')

  const { data: clients = [] } = useQuery({
    queryKey: ['protocol-clients'],
    queryFn: () => api.listClients(),
  })

  useEffect(() => {
    if (tenantId === 'default' && Array.isArray(clients) && clients[0]?.id) {
      setTenantId(clients[0].id)
    }
  }, [clients, tenantId])

  const { data: mcpServers = [] } = useQuery({
    queryKey: ['protocol-mcp-servers', tenantId],
    queryFn: () => api.listProtocolMcpServers(tenantId),
    enabled: !!tenantId,
  })

  const { data: a2aPeers = [] } = useQuery({
    queryKey: ['protocol-a2a-peers', tenantId],
    queryFn: () => api.listA2aPeers(tenantId),
    enabled: !!tenantId,
  })

  const handshakeMutation = useMutation({
    mutationFn: () => api.dryRunA2aHandshake(peerUrl),
    onSuccess: () => toast.success('Handshake dry-run executado.'),
    onError: (error: any) => toast.error(error?.message || 'Falha no handshake'),
  })

  const trustExplainMutation = useMutation({
    mutationFn: () => api.explainProtocolTrust(trustProtocol, trustEntityId),
    onError: (error: any) => toast.error(error?.message || 'Falha ao avaliar trust'),
  })

  const approveToolMutation = useMutation({
    mutationFn: ({ serverId, toolName }: { serverId: string; toolName: string }) => api.approveProtocolMcpTool(serverId, toolName),
    onSuccess: () => {
      toast.success('Tool aprovada.')
      queryClient.invalidateQueries({ queryKey: ['protocol-mcp-servers'] })
    },
    onError: (error: any) => toast.error(error?.message || 'Falha ao aprovar tool'),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-foreground">Agent Protocols</h1>
        <p className="text-sm md:text-lg text-muted-foreground">Cobertura real para MCP servers, peers A2A e explicacao de trust.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
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
          <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Peer URL</span>
          <input value={peerUrl} onChange={e => setPeerUrl(e.target.value)} className={inputClassName} placeholder="https://peer.example/a2a" />
        </label>
        <div className="flex items-end">
          <button type="button" onClick={() => handshakeMutation.mutate()} disabled={!peerUrl.trim()} className="w-full rounded-xl bg-primary px-4 py-3 text-sm font-bold text-white hover:bg-primary/90 disabled:opacity-50">
            <Play className="mr-2 inline h-4 w-4" />
            Dry-run Handshake
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="MCP Servers" value={String(mcpServers.length)} icon={<Server className="h-5 w-5" />} />
        <MetricCard label="A2A Peers" value={String(a2aPeers.length)} icon={<Users className="h-5 w-5 text-primary" />} />
        <MetricCard label="Trust Checks" value={trustExplainMutation.data ? '1' : '0'} icon={<ShieldCheck className="h-5 w-5" />} />
        <MetricCard label="Tenant" value={tenantId ? 'ativo' : 'n/a'} icon={<Network className="h-5 w-5" />} />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="MCP Servers">
          <div className="space-y-4">
            {mcpServers.length ? mcpServers.map((server: any) => (
              <div key={server.id} className="rounded-2xl border border-border bg-background p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-bold text-foreground">{server.name}</div>
                    <div className="text-xs text-muted-foreground">{server.endpoint || server.base_url || '-'}</div>
                  </div>
                  <span className="rounded-full bg-primary/10 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-primary">
                    {server.trust_level || 'unknown'}
                  </span>
                </div>
                {Array.isArray(server.discovered_tools) && server.discovered_tools.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {server.discovered_tools.map((tool: any) => {
                      const toolName = typeof tool === 'string' ? tool : tool.name
                      return (
                        <button
                          key={toolName}
                          type="button"
                          onClick={() => approveToolMutation.mutate({ serverId: server.id, toolName })}
                          className="rounded-full border border-border px-3 py-1 text-[10px] font-black uppercase tracking-widest hover:bg-secondary"
                        >
                          {toolName}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            )) : (
              <div className="rounded-2xl border border-dashed border-border p-6 text-sm text-muted-foreground">Nenhum MCP server retornado.</div>
            )}
          </div>
        </Card>

        <Card title="A2A Peers">
          <JsonList values={a2aPeers} />
        </Card>
      </div>

      <Card title="Trust Explain">
        <div className="grid gap-4 md:grid-cols-3">
          <label className="space-y-2">
            <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Protocol</span>
            <select value={trustProtocol} onChange={e => setTrustProtocol(e.target.value)} className={inputClassName}>
              <option value="mcp">mcp</option>
              <option value="a2a">a2a</option>
            </select>
          </label>
          <label className="space-y-2 md:col-span-2">
            <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Entity ID</span>
            <input value={trustEntityId} onChange={e => setTrustEntityId(e.target.value)} className={inputClassName} placeholder="UUID do server ou peer" />
          </label>
        </div>
        <div className="mt-4 flex justify-end">
          <button type="button" onClick={() => trustExplainMutation.mutate()} disabled={!trustEntityId.trim()} className="rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:bg-primary/90 disabled:opacity-50">
            Avaliar
          </button>
        </div>
        {trustExplainMutation.data && (
          <pre className="mt-4 overflow-x-auto rounded-2xl bg-background p-3 text-[10px] text-foreground">
            {JSON.stringify(trustExplainMutation.data, null, 2)}
          </pre>
        )}
      </Card>
    </div>
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
