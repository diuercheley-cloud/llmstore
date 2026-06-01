import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../../lib/api'
import { Network, Server, Wrench, ShieldCheck, Activity, Plus, RefreshCw, Zap } from 'lucide-react'
import { toast } from 'sonner'

export default function MCPDashboard() {
  const queryClient = useQueryClient()
  const [isRegistering, setIsRegistering] = useState(false)
  const [tenantId, setTenantId] = useState('')
  const [serverName, setServerName] = useState('')
  const [transport, setTransport] = useState('streamable_http')
  const [endpoint, setEndpoint] = useState('')
  const [trustLevel, setTrustLevel] = useState('untrusted')

  const { data: servers, isLoading: serversLoading } = useQuery({
    queryKey: ['mcp-servers'],
    queryFn: () => api.listMcpServers()
  })

  const { data: tools, isLoading: toolsLoading } = useQuery({
    queryKey: ['mcp-tools'],
    queryFn: () => api.listMcpTools()
  })

  const { data: clientsData, isLoading: clientsLoading } = useQuery<any>({
    queryKey: ['clients-for-mcp'],
    queryFn: () => api.listClients()
  })

  const clients = Array.isArray(clientsData) ? clientsData : clientsData?.items || []

  useEffect(() => {
    if (!tenantId && clients.length > 0) {
      setTenantId(clients[0].id)
    }
  }, [clients, tenantId])

  const discoverMutation = useMutation({
    mutationFn: (id: string) => api.discoverMcpTools(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-tools'] })
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] })
    }
  })

  const approveMutation = useMutation({
    mutationFn: ({ serverId, toolName }: { serverId: string, toolName: string }) => 
      api.approveMcpTool(serverId, toolName),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mcp-tools'] })
  })

  const registerMutation = useMutation({
    mutationFn: (payload: { tenant_id: string; name: string; transport: string; endpoint: string; trust_level: string }) =>
      api.registerMcpServer(payload),
    onSuccess: async () => {
      toast.success('Servidor MCP registrado com sucesso')
      setIsRegistering(false)
      setServerName('')
      setEndpoint('')
      setTransport('streamable_http')
      setTrustLevel('untrusted')
      await queryClient.invalidateQueries({ queryKey: ['mcp-servers'] })
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : 'Falha ao registrar servidor MCP')
    }
  })

  const handleRegisterServer = () => {
    if (!tenantId.trim() || !serverName.trim() || !endpoint.trim()) {
      toast.error('Preencha tenant, nome e endpoint do servidor MCP')
      return
    }

    registerMutation.mutate({
      tenant_id: tenantId.trim(),
      name: serverName.trim(),
      transport,
      endpoint: endpoint.trim(),
      trust_level: trustLevel,
    })
  }

  if (serversLoading || toolsLoading || clientsLoading) return <div className="p-8">Carregando MCP Stack...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Model Context <span className="text-primary">Protocol</span></h1>
          <p className="text-muted-foreground font-medium text-lg">Integração padronizada de ferramentas e recursos externos.</p>
        </div>
        <button 
          onClick={() => setIsRegistering(true)}
          className="bg-primary text-primary-foreground px-6 py-3 rounded-2xl font-bold flex items-center gap-2 hover:opacity-90 transition-all shadow-lg shadow-primary/20"
        >
          <Plus className="w-5 h-5" />
          Novo Servidor MCP
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1 space-y-6">
          <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1">Servidores Registrados</h2>
          <div className="space-y-4">
            {servers?.map((server: any) => (
              <div key={server.id} className="bg-card border border-border rounded-3xl p-5 hover:border-primary/50 transition-all">
                <div className="flex justify-between items-start mb-4">
                  <div className="p-3 bg-primary/10 text-primary rounded-2xl">
                    <Server className="w-6 h-6" />
                  </div>
                  <span className={`px-2 py-1 rounded text-[10px] font-black uppercase tracking-tighter ${
                    server.trust_level === 'trusted' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-amber-500/10 text-amber-600'
                  }`}>
                    {server.trust_level}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-foreground mb-1">{server.name}</h3>
                <p className="text-xs text-muted-foreground font-mono mb-4 break-all">{server.endpoint}</p>
                
                <div className="flex items-center justify-between pt-4 border-t border-border">
                  <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">{server.transport}</span>
                  <button 
                    onClick={() => discoverMutation.mutate(server.id)}
                    disabled={discoverMutation.isPending}
                    className="flex items-center gap-2 text-primary hover:text-primary/80 transition-all text-xs font-bold"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${discoverMutation.isPending ? 'animate-spin' : ''}`} />
                    Discover
                  </button>
                </div>
              </div>
            ))}
            {(!servers || servers.length === 0) && (
              <div className="p-10 border-2 border-dashed border-border rounded-3xl text-center">
                <p className="text-sm text-muted-foreground">Nenhum servidor MCP configurado.</p>
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1">Ferramentas Descobertas</h2>
          <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-muted/50 border-bottom border-border">
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Ferramenta</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Servidor</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Status</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground text-right">Ação</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {tools?.map((tool: any) => (
                  <tr key={`${tool.server_id}-${tool.name}`} className="hover:bg-muted/30 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-bold text-foreground">{tool.name}</div>
                      <div className="text-xs text-muted-foreground line-clamp-1">{tool.description}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-medium text-muted-foreground">{tool.server_id.slice(0, 8)}</span>
                    </td>
                    <td className="px-6 py-4">
                      {tool.approved ? (
                        <div className="flex items-center gap-1.5 text-emerald-600 text-[10px] font-black uppercase">
                          <ShieldCheck className="w-3.5 h-3.5" />
                          Approved
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-amber-600 text-[10px] font-black uppercase">
                          <Activity className="w-3.5 h-3.5" />
                          Pending
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {!tool.approved && (
                        <button 
                          onClick={() => approveMutation.mutate({ serverId: tool.server_id, toolName: tool.name })}
                          className="bg-foreground text-background px-3 py-1.5 rounded-lg text-[10px] font-black uppercase hover:opacity-90 transition-all"
                        >
                          Approve
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {(!tools || tools.length === 0) && (
                  <tr>
                    <td colSpan={4} className="px-6 py-20 text-center text-muted-foreground">
                      Nenhuma ferramenta encontrada. Inicie a descoberta em um servidor.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {isRegistering && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-foreground/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-3xl border border-border bg-card shadow-2xl">
            <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
              <div>
                <h2 className="text-xl font-black text-foreground">Novo Servidor MCP</h2>
                <p className="text-sm text-muted-foreground">Registra um endpoint MCP persistente no backend administrativo.</p>
              </div>
              <button
                onClick={() => setIsRegistering(false)}
                className="rounded-xl border border-border px-3 py-2 text-sm font-bold text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                Fechar
              </button>
            </div>

            <div className="grid gap-4 px-6 py-5 md:grid-cols-2">
              <label className="block space-y-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Tenant ID</span>
                <select
                  value={tenantId}
                  onChange={e => setTenantId(e.target.value)}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                >
                  <option value="">Selecione um cliente/tenant</option>
                  {clients.map((client: any) => (
                    <option key={client.id} value={client.id}>
                      {client.name} {client.billing_status ? `· ${client.billing_status}` : ''}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Nome</span>
                <input
                  value={serverName}
                  onChange={e => setServerName(e.target.value)}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                  placeholder="Ex: Filesystem MCP"
                />
              </label>

              <label className="block space-y-2 md:col-span-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Endpoint</span>
                <input
                  value={endpoint}
                  onChange={e => setEndpoint(e.target.value)}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                  placeholder="http://localhost:8000/mcp"
                />
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Transport</span>
                <select
                  value={transport}
                  onChange={e => setTransport(e.target.value)}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                >
                  <option value="streamable_http">streamable_http</option>
                  <option value="sse">sse</option>
                  <option value="stdio">stdio</option>
                </select>
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Trust Level</span>
                <select
                  value={trustLevel}
                  onChange={e => setTrustLevel(e.target.value)}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                >
                  <option value="untrusted">untrusted</option>
                  <option value="trusted">trusted</option>
                </select>
              </label>
            </div>

            <div className="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
              <button
                onClick={() => setIsRegistering(false)}
                className="rounded-2xl border border-border px-4 py-2.5 text-sm font-bold text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                Cancelar
              </button>
              <button
                onClick={handleRegisterServer}
                disabled={registerMutation.isPending}
                className="rounded-2xl bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground hover:opacity-90 disabled:opacity-60"
              >
                {registerMutation.isPending ? 'Registrando...' : 'Registrar Servidor'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
