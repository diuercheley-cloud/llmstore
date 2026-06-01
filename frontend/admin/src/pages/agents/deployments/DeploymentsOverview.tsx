import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../../lib/api'
import { FastForward, Rocket, CheckCircle2, AlertCircle, Clock, PauseCircle, Archive } from 'lucide-react'
import { LoadingCard } from '../../../components/ui-feedback'

export default function DeploymentsOverview() {
  const queryClient = useQueryClient()

  const { data: deployments = [], isLoading } = useQuery({
    queryKey: ['deployments'],
    queryFn: () => api.listDeployments()
  })

  const rollbackMutation = useMutation({
    mutationFn: (id: string) => api.rollbackDeployment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deployments'] })
    }
  })

  const promoteMutation = useMutation({
    mutationFn: (id: string) => api.promoteDeployment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deployments'] })
    }
  })

  const pauseMutation = useMutation({
    mutationFn: (id: string) => api.pauseDeployment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deployments'] })
    }
  })

  const resumeMutation = useMutation({
    mutationFn: (id: string) => api.resumeDeployment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deployments'] })
    }
  })

  if (isLoading) return <LoadingCard />

  const handleDetails = (dep: any) => {
    alert(`Detalhes do Deployment: ${dep.name || dep.slug}\nID: ${dep.id}\nStatus: ${dep.status}\nVersão: ${dep.version}`);
  };

  const handleNewRelease = () => {
    alert("Iniciando novo fluxo de release... Esta funcionalidade requer a seleção de um bundle do Registry (em breve).");
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10">
        <h1 className="text-4xl font-black text-foreground tracking-tight">Canary & <span className="text-primary">CI/CD</span></h1>
        <p className="text-muted-foreground font-medium text-lg">Gerenciamento de deployments progressivos e integridade de versões.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1">Deployments Ativos</h2>
          <div className="space-y-4">
            {deployments.map((dep: any) => (
              <div key={dep.id} className="bg-card border border-border rounded-3xl p-6 hover:border-primary/30 transition-all">
                <div className="flex justify-between items-start mb-6">
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-2xl ${
                      dep.status === 'canary' ? 'bg-amber-500/10 text-amber-600' :
                      dep.status === 'active' ? 'bg-emerald-500/10 text-emerald-600' : 
                      dep.status === 'paused' ? 'bg-slate-500/10 text-slate-400' :
                      dep.status === 'archived' ? 'bg-slate-800/50 text-slate-500' :
                      'bg-destructive/10 text-destructive'
                    }`}>
                      {dep.status === 'canary' ? <FastForward className="w-6 h-6" /> : 
                       dep.status === 'paused' ? <PauseCircle className="w-6 h-6" /> :
                       dep.status === 'archived' ? <Archive className="w-6 h-6" /> :
                       <Rocket className="w-6 h-6" />}
                    </div>
                    <div>
                      <h3 className="text-xl font-black text-foreground">{dep.name || dep.slug}</h3>
                      <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
                        v{dep.version || '0.1.0'} • {new Date(dep.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-black text-foreground">{dep.status === 'active' ? '100%' : dep.status === 'canary' ? '10%' : '0%'}</div>
                    <div className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Tráfego</div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-border">
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1.5">
                      <div className={`w-2 h-2 rounded-full ${dep.status === 'active' || dep.status === 'canary' ? 'bg-emerald-500' : 'bg-destructive'}`} />
                      <span className="text-[10px] font-black uppercase text-muted-foreground">Status: {dep.status}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {dep.status === 'paused' ? (
                       <button onClick={() => resumeMutation.mutate(dep.id)} className="text-xs font-bold px-4 py-2 bg-emerald-500/10 text-emerald-600 rounded-xl transition-all">Resume</button>
                    ) : (dep.status === 'active' || dep.status === 'canary') ? (
                       <button onClick={() => pauseMutation.mutate(dep.id)} className="text-xs font-bold px-4 py-2 hover:bg-muted rounded-xl transition-all">Pause</button>
                    ) : null}

                    {dep.status !== 'archived' && (
                       <button onClick={() => rollbackMutation.mutate(dep.id)} className="text-xs font-bold px-4 py-2 hover:bg-muted rounded-xl transition-all">Rollback</button>
                    )}
                    <button 
                      onClick={() => dep.status === 'canary' ? promoteMutation.mutate(dep.id) : handleDetails(dep)}
                      className="bg-foreground text-background text-xs font-bold px-4 py-2 rounded-xl hover:opacity-90 transition-all"
                    >
                      {dep.status === 'canary' ? 'Promote' : 'Details'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
            {deployments.length === 0 && (
              <div className="text-center py-10 text-muted-foreground border border-dashed border-border rounded-3xl">Nenhum deployment ativo.</div>
            )}
          </div>
        </div>

        <div className="space-y-8">
           <section>
              <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1 mb-4">Pipeline Status</h2>
              <div className="bg-card border border-border rounded-3xl p-6 space-y-6">
                 {[
                   { label: 'Agent Build', status: 'success', time: '1m 12s' },
                   { label: 'Eval Suite (Security)', status: 'success', time: '4m 45s' },
                   { label: 'Eval Suite (Performance)', status: 'running', time: '2m 10s' },
                   { label: 'Canary Deployment', status: 'pending', time: '-' },
                 ].map((step, i) => (
                   <div key={i} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                         {step.status === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> :
                          step.status === 'running' ? <Clock className="w-4 h-4 text-primary animate-spin" /> :
                          <AlertCircle className="w-4 h-4 text-muted-foreground" />}
                         <span className="text-sm font-medium">{step.label}</span>
                      </div>
                      <span className="text-[10px] font-mono text-muted-foreground">{step.time}</span>
                   </div>
                 ))}
              </div>
           </section>

           <div className="bg-primary text-primary-foreground rounded-3xl p-6 shadow-xl shadow-primary/20">
              <h3 className="text-lg font-black uppercase tracking-tight mb-2">Novo Deployment</h3>
              <p className="text-xs opacity-80 mb-6 leading-relaxed">
                Inicie um novo fluxo de deployment selecionando um bundle assinado do Registry.
              </p>
              <button 
                onClick={handleNewRelease}
                className="w-full py-3 bg-background text-foreground rounded-2xl text-[10px] font-black uppercase tracking-widest hover:opacity-90 transition-all"
              >
                Iniciar Release
              </button>
           </div>
        </div>
      </div>
    </div>
  )
}
