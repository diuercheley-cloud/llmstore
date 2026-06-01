import { useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { FlaskConical, Play, AlertOctagon, History, ShieldCheck, FileText, AlertTriangle, ShieldAlert } from 'lucide-react'

export default function ChaosDashboard() {
  const queryClient = useQueryClient()

  const { data: experiments, isLoading: experimentsLoading } = useQuery({
    queryKey: ['chaos-experiments'],
    queryFn: async () => {
      const res = await api.get('/admin/chaos/experiments')
      return res.data
    }
  })

  const { data: chaosStatus } = useQuery({
    queryKey: ['chaos-status'],
    queryFn: async () => {
      const res = await api.get('/admin/chaos/status')
      return res.data
    }
  })

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: ['chaos-runs'],
    queryFn: async () => {
      const res = await api.get('/admin/chaos/runs')
      return res.data
    }
  })

  const runMutation = useMutation({
    mutationFn: async (id: string) => {
      if (!confirm('Este experimento irá injetar falhas no ambiente. Confirmar?')) return
      return api.post('/admin/chaos/runs', { experiment_id: id })
    },
    onSuccess: () => {
      alert('Experimento iniciado com sucesso!')
      queryClient.invalidateQueries({ queryKey: ['chaos-runs'] })
      queryClient.invalidateQueries({ queryKey: ['chaos-status'] })
    }
  })

  const abortMutation = useMutation({
    mutationFn: async (id: string) => api.post(`/admin/chaos/runs/${id}/abort`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chaos-runs'] })
  })

  const stats = useMemo(() => {
    const items = Array.isArray(runs) ? runs : []
    return {
      totalRuns: items.length,
      completed: items.filter((run: any) => run.status === 'completed').length,
      running: items.filter((run: any) => run.status === 'running').length,
      failed: items.filter((run: any) => run.status === 'failed').length,
    }
  }, [runs])

  const statusVariant = chaosStatus?.state === 'operational'
    ? 'bg-emerald-50 text-emerald-700 border-emerald-100'
    : chaosStatus?.state === 'blocked'
      ? 'bg-amber-50 text-amber-700 border-amber-100'
      : 'bg-red-50 text-red-700 border-red-100'

  if (experimentsLoading || runsLoading) return <div className="p-8">Carregando catálogo de chaos...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Chaos <span className="text-destructive">Engineering</span></h1>
          <p className="text-muted-foreground font-medium text-lg">Injeção controlada de falhas para validação de resiliência.</p>
        </div>
        <div className="flex gap-4">
           <div className={`flex items-center gap-2 px-4 py-2 rounded-2xl border ${statusVariant}`}>
             {chaosStatus?.state === 'operational' ? (
               <ShieldCheck className="w-4 h-4" />
             ) : chaosStatus?.state === 'blocked' ? (
               <ShieldAlert className="w-4 h-4" />
             ) : (
               <AlertTriangle className="w-4 h-4" />
             )}
             <span className="text-xs font-black uppercase">
               Safety: {chaosStatus?.state || 'unknown'}
             </span>
           </div>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Experimentos</div>
          <div className="text-3xl font-black text-foreground">{experiments?.length || 0}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Runs</div>
          <div className="text-3xl font-black text-foreground">{stats.totalRuns}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Concluídos</div>
          <div className="text-3xl font-black text-emerald-600">{stats.completed}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Falhos / em execução</div>
          <div className="text-3xl font-black text-rose-600">{stats.failed + stats.running}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1">Catálogo de Experimentos</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {experiments?.map((exp: any) => (
              <div key={exp.id} className="bg-card border border-border rounded-3xl p-6 hover:border-destructive transition-all group">
                <div className="flex justify-between items-start mb-4">
                  <div className="p-3 bg-destructive/10 text-destructive rounded-2xl group-hover:bg-destructive group-hover:text-white transition-colors">
                    <FlaskConical className="w-6 h-6" />
                  </div>
                  <span className={`px-2 py-1 rounded text-[10px] font-black uppercase tracking-tighter ${
                    exp.blast_radius === 'high' ? 'bg-destructive/20 text-destructive' : 
                    exp.blast_radius === 'medium' ? 'bg-yellow-500/20 text-yellow-600' : 'bg-accent/20 text-blue-700'
                  }`}>
                    Radius: {exp.blast_radius}
                  </span>
                </div>
                <h3 className="text-xl font-black text-foreground mb-2">{exp.name}</h3>
                <p className="text-sm text-muted-foreground mb-6 line-clamp-2 font-medium">{exp.description}</p>
                
                <div className="flex items-center justify-between pt-4 border-t border-border">
                  <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">{exp.experiment_type}</span>
                  <button 
                    onClick={() => runMutation.mutate(exp.id)}
                    className="flex items-center gap-2 bg-foreground text-background px-4 py-2 rounded-xl text-xs font-bold hover:bg-destructive transition-all"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    Rodar
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-6">
           <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1">Atividade Recente</h2>
           <div className="bg-foreground text-background rounded-3xl p-6 shadow-xl shadow-slate-900/10">
              <div className="flex items-center gap-2 mb-6 text-destructive">
                <History className="w-5 h-5" />
                <h3 className="font-black uppercase tracking-tight text-sm">Últimos Runs</h3>
              </div>
              <div className="space-y-4">
                 {runs?.length ? runs.slice(0, 4).map((run: any) => (
                   <div key={run.id} className="p-4 rounded-2xl bg-foreground/50 border border-border/50 flex flex-col gap-3 hover:border-rose-500/50 transition-colors">
                      <div className="flex justify-between items-start gap-4">
                        <div>
                          <div className="font-bold text-sm mb-1">{run.experiment_name || 'Exp. sem nome'}</div>
                          <div className="text-[10px] font-mono text-muted-foreground">{run.id.slice(0, 8)} • {run.environment}</div>
                        </div>
                        <span className={`text-[10px] font-black px-2 py-1 rounded uppercase tracking-tighter ${
                          run.status === 'completed'
                            ? 'bg-emerald-500/10 text-emerald-600'
                            : run.status === 'running'
                              ? 'bg-primary/10 text-primary'
                              : run.status === 'failed'
                                ? 'bg-destructive/10 text-destructive'
                                : 'bg-secondary text-muted-foreground'
                        }`}>
                          {run.status}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-2 text-[10px] text-muted-foreground">
                        <span>{run.started_at ? new Date(run.started_at).toLocaleString('pt-BR') : 'Aguardando início'}</span>
                        {run.status === 'running' ? (
                          <button
                            onClick={() => abortMutation.mutate(run.id)}
                            className="text-xs font-black uppercase tracking-widest text-destructive hover:text-destructive/80"
                          >
                            Abort
                          </button>
                        ) : run.status === 'completed' ? (
                          <button
                            onClick={async () => {
                              const res = await api.get(`/admin/chaos/runs/${run.id}/report`)
                              alert(res.data.summary || 'Relatório disponível')
                            }}
                            className="text-xs font-black uppercase tracking-widest text-primary hover:text-primary/80"
                          >
                            Report
                          </button>
                        ) : run.status === 'failed' && run.error_message ? (
                          <span className="max-w-[14rem] text-right text-[10px] leading-relaxed text-rose-300">
                            {run.error_message}
                          </span>
                        ) : (
                          <FileText className="w-4 h-4 text-muted-foreground" />
                        )}
                      </div>
                   </div>
                 )) : (
                   <div className="p-4 rounded-2xl bg-foreground/50 border border-border/50 text-sm text-muted-foreground">
                     Nenhum run registrado ainda.
                   </div>
                 )}
              </div>
              <button className="w-full mt-6 py-3 rounded-2xl bg-foreground text-[10px] font-black uppercase tracking-widest hover:bg-foreground/90 transition-colors">
                {chaosStatus?.operational ? 'Ambiente apto para execução' : 'Execução restrita'}
              </button>
           </div>

           <div className="bg-destructive/10 border border-rose-100 rounded-3xl p-6">
              <div className="flex items-center gap-2 mb-3 text-destructive">
                <AlertOctagon className="w-5 h-5" />
                <h3 className="font-black uppercase tracking-tight text-sm">Emergência</h3>
              </div>
              <p className="text-xs text-destructive font-medium mb-4 leading-relaxed">
                Em caso de instabilidade não prevista, aborte todos os experimentos ativos imediatamente.
              </p>
              <button className="w-full py-3 rounded-2xl bg-destructive text-white text-[10px] font-black uppercase tracking-widest hover:bg-destructive/90 transition-colors shadow-lg shadow-rose-200">
                Abort All Experiments
              </button>
           </div>
        </div>
      </div>
    </div>
  )
}
