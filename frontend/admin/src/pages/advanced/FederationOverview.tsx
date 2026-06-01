import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import { Share2, Network, ShieldCheck, AlertTriangle, History, Download, Plus, RefreshCw } from 'lucide-react'
import { LoadingCard } from '../../components/ui-feedback'

export default function FederationOverview() {
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['federation-status'],
    queryFn: () => api.getFederationStatus()
  })

  const { data: peers, isLoading: peersLoading } = useQuery({
    queryKey: ['federation-peers'],
    queryFn: () => api.listFederationPeers()
  })

  const { data: audit, isLoading: auditLoading } = useQuery({
    queryKey: ['federation-audit'],
    queryFn: () => api.listFederationAudit()
  })

  if (statusLoading || peersLoading) return <LoadingCard />

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Governance <span className="text-primary">Federation</span></h1>
          <p className="text-muted-foreground font-medium text-lg">Sincronização de políticas e auditoria entre clusters distribuídos.</p>
        </div>
        <div className="flex gap-3">
          <button className="bg-card border border-border px-4 py-3 rounded-2xl font-bold flex items-center gap-2 hover:bg-muted transition-all">
            <Download className="w-5 h-5" />
            Exportar Relatório
          </button>
          <button className="bg-primary text-primary-foreground px-6 py-3 rounded-2xl font-bold flex items-center gap-2 hover:opacity-90 transition-all shadow-lg shadow-primary/20">
            <Plus className="w-5 h-5" />
            Registrar Peer
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Total Peers</div>
          <div className="text-3xl font-black text-foreground">{status?.total_peers || 0}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Clusters Online</div>
          <div className="text-3xl font-black text-emerald-600">{status?.online_peers || 0}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Sync Mode</div>
          <div className="text-3xl font-black text-primary capitalize">{status?.mode || 'manual'}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Consistência</div>
          <div className="flex items-center gap-2">
            <div className="text-3xl font-black text-foreground">98.2%</div>
            <ShieldCheck className="w-6 h-6 text-emerald-500" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <section>
            <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1 mb-4">Clusters Federados</h2>
            <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-muted/50 border-bottom border-border">
                    <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Cluster ID</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Região</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Status</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Last Sync</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground text-right">Trust</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {peers?.map((peer: any) => (
                    <tr key={peer.peer_cluster_id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-bold text-foreground">{peer.peer_cluster_id}</div>
                        <div className="text-[10px] text-muted-foreground font-mono">{peer.environment}</div>
                      </td>
                      <td className="px-6 py-4 text-xs font-medium text-muted-foreground">
                        {peer.region || 'global'}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-[10px] font-black uppercase tracking-tighter ${
                          peer.status === 'active' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-destructive/10 text-destructive'
                        }`}>
                          {peer.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-xs text-muted-foreground">
                        {peer.last_policy_sync_at ? new Date(peer.last_policy_sync_at).toLocaleString('pt-BR') : '-'}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-[10px] font-black uppercase px-2 py-1 bg-muted rounded">
                          {peer.trust_level}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1 mb-4">Recentes Sincronizações</h2>
            <div className="space-y-3">
              {status?.recent_syncs?.map((sync: any) => (
                <div key={sync.id} className="bg-card border border-border rounded-2xl p-4 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="p-2 bg-primary/10 text-primary rounded-xl">
                      <RefreshCw className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-sm font-bold">{sync.bundle_name} v{sync.bundle_version}</div>
                      <div className="text-[10px] text-muted-foreground uppercase tracking-widest">{sync.sync_direction}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-[10px] font-black uppercase ${sync.status === 'success' ? 'text-emerald-600' : 'text-amber-600'}`}>
                      {sync.status}
                    </div>
                    <div className="text-[10px] text-muted-foreground">{new Date(sync.created_at).toLocaleTimeString()}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="space-y-8">
          <section>
            <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1 mb-4">Auditoria Global</h2>
            <div className="bg-foreground text-background rounded-3xl p-6 shadow-xl">
              <div className="flex items-center gap-2 mb-6 text-primary">
                <History className="w-5 h-5" />
                <h3 className="font-black uppercase tracking-tight text-sm">Audit Trail</h3>
              </div>
              <div className="space-y-4">
                {audit?.recent_events?.map((event: any, i: number) => (
                  <div key={i} className="border-l-2 border-primary/30 pl-4 py-1">
                    <div className="text-xs font-bold text-foreground-muted">{event.event_type}</div>
                    <div className="text-[10px] text-muted-foreground mb-1">{event.source_cluster_id}</div>
                    <div className="text-[10px] font-mono text-primary/80">{new Date(event.received_at).toLocaleTimeString()}</div>
                  </div>
                ))}
              </div>
              <button className="w-full mt-6 py-3 rounded-2xl bg-primary text-primary-foreground text-[10px] font-black uppercase tracking-widest hover:opacity-90 transition-colors">
                Ver Logs Completos
              </button>
            </div>
          </section>

          <div className="bg-amber-50 border border-amber-100 rounded-3xl p-6">
            <div className="flex items-center gap-2 mb-3 text-amber-600">
              <AlertTriangle className="w-5 h-5" />
              <h3 className="font-black uppercase tracking-tight text-sm">Integridade</h3>
            </div>
            <p className="text-xs text-amber-700 font-medium leading-relaxed">
              Existem 2 clusters com versões de políticas divergentes. Recomenda-se sincronização forçada.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
