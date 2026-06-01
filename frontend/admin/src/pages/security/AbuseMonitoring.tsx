import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { ShieldAlert, AlertOctagon, UserX, CheckCircle, Activity, History, Filter, ShieldEllipsis } from 'lucide-react'
import { useState } from 'react'

export default function AbuseMonitoring() {
  const queryClient = useQueryClient()
  const [severityFilter, setSeverityFilter] = useState<string | null>(null)

  const { data: summary } = useQuery({
    queryKey: ['abuse-summary'],
    queryFn: () => api.getAbuseSummary()
  })

  const { data: events, isLoading: eventsLoading } = useQuery({
    queryKey: ['abuse-events', severityFilter],
    queryFn: () => api.listAbuseEvents(200)
  })

  const ackMutation = useMutation({
    mutationFn: (id: string) => api.ackAbuseAction(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['abuse-events'] })
      queryClient.invalidateQueries({ queryKey: ['abuse-summary'] })
    }
  })

  const suspendMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string, reason: string }) => api.suspendClient(id, reason),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['abuse-summary'] })
  })

  if (eventsLoading) return <div className="p-8">Monitorando sinais de abuso...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Abuse <span className="text-destructive">Monitoring</span></h1>
          <p className="text-muted-foreground font-medium text-lg">Detecção proativa de comportamentos maliciosos e violação de ToS.</p>
        </div>
        <div className="flex gap-4">
           <div className="bg-destructive/10 text-destructive border border-destructive/20 px-4 py-2 rounded-2xl flex items-center gap-2">
             <AlertOctagon className="w-4 h-4" />
             <span className="text-xs font-black uppercase tracking-widest">Atividade Suspeita: {summary?.active_alerts || 0}</span>
           </div>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Sinais Totais (24h)</div>
          <div className="text-3xl font-black text-foreground">{summary?.total_signals_24h || 0}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Clientes Suspensos</div>
          <div className="text-3xl font-black text-rose-600">{summary?.suspended_clients || 0}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">High Severity</div>
          <div className="text-3xl font-black text-destructive">{summary?.high_severity_alerts || 0}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Auto-mitigados</div>
          <div className="text-3xl font-black text-emerald-600">{summary?.auto_mitigated || 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="flex justify-between items-center px-1">
            <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest">Feed de Eventos de Segurança</h2>
            <div className="flex gap-2">
              <button onClick={() => setSeverityFilter(null)} className={`px-3 py-1 rounded-lg text-[10px] font-bold uppercase transition-all ${!severityFilter ? 'bg-foreground text-background' : 'bg-muted text-muted-foreground'}`}>Todos</button>
              <button onClick={() => setSeverityFilter('high')} className={`px-3 py-1 rounded-lg text-[10px] font-bold uppercase transition-all ${severityFilter === 'high' ? 'bg-destructive text-white' : 'bg-destructive/10 text-destructive'}`}>Críticos</button>
            </div>
          </div>
          
          <div className="space-y-4">
            {events?.map((event: any) => (
              <div key={event.id} className={`bg-card border rounded-3xl p-6 transition-all ${event.severity === 'high' ? 'border-destructive/30 hover:border-destructive' : 'border-border hover:border-primary/30'}`}>
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-2xl ${event.severity === 'high' ? 'bg-destructive/10 text-destructive' : 'bg-amber-500/10 text-amber-600'}`}>
                      <ShieldEllipsis className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-foreground">{event.signal_type}</h3>
                      <div className="text-xs text-muted-foreground font-mono">{event.client_id}</div>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded text-[10px] font-black uppercase tracking-tighter ${
                    event.severity === 'high' ? 'bg-destructive/20 text-destructive' : 'bg-amber-500/10 text-amber-600'
                  }`}>
                    {event.severity}
                  </span>
                </div>
                
                <p className="text-sm text-muted-foreground mb-6 leading-relaxed font-medium">
                  {event.description}
                </p>

                <div className="flex items-center justify-between pt-4 border-t border-border">
                  <div className="text-[10px] font-bold text-muted-foreground uppercase">{new Date(event.created_at).toLocaleString('pt-BR')}</div>
                  <div className="flex gap-2">
                    <button className="text-xs font-bold px-4 py-2 hover:bg-muted rounded-xl transition-all">Analisar</button>
                    {!event.acknowledged && (
                      <button 
                        onClick={() => ackMutation.mutate(event.id)}
                        className="bg-foreground text-background text-xs font-bold px-4 py-2 rounded-xl hover:opacity-90 transition-all"
                      >
                        Acknowledge
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-8">
          <section>
            <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1 mb-4">Ações Rápidas</h2>
            <div className="bg-foreground text-background rounded-3xl p-6 shadow-xl">
               <div className="flex items-center gap-2 mb-6 text-destructive">
                 <UserX className="w-5 h-5" />
                 <h3 className="font-black uppercase tracking-tight text-sm">Contenção</h3>
               </div>
               <div className="space-y-4">
                  <div className="p-4 rounded-2xl bg-background/5 border border-border/10">
                    <div className="text-xs font-bold mb-2">Suspender Client por ID</div>
                    <input type="text" placeholder="UUID do Cliente" className="w-full bg-background/10 border border-border/20 rounded-xl px-4 py-2 text-xs outline-none focus:border-primary transition-all mb-3" />
                    <button className="w-full py-2 bg-destructive text-white text-[10px] font-black uppercase tracking-widest rounded-xl hover:opacity-90">
                      Suspender Imediatamente
                    </button>
                  </div>
               </div>
            </div>
          </section>

          <section>
            <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1 mb-4">Top Atividade de Risco</h2>
            <div className="bg-card border border-border rounded-3xl p-6 space-y-4">
               {summary?.top_risk_clients?.map((client: any, i: number) => (
                 <div key={i} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                    <div>
                      <div className="text-sm font-bold">{client.name || 'Anonymous'}</div>
                      <div className="text-[10px] font-mono text-muted-foreground">{client.id.slice(0, 8)}</div>
                    </div>
                    <div className="text-right">
                       <div className="text-xs font-black text-rose-600">{client.risk_score}</div>
                       <div className="text-[8px] font-black uppercase text-muted-foreground">Score</div>
                    </div>
                 </div>
               ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
