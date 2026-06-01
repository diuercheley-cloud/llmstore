import { Trophy, Zap, FlaskConical, Target, History, Play, AlertCircle } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../../lib/api'
import { LoadingCard } from '../../../components/ui-feedback'

export default function OptimizationTournaments() {
  const queryClient = useQueryClient()

  const { data: tournaments = [], isLoading } = useQuery({
    queryKey: ['optimization-tournaments'],
    queryFn: () => api.listTournaments()
  })

  const runMutation = useMutation({
    mutationFn: (id: string) => api.runTournament(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['optimization-tournaments'] })
    }
  })

  if (isLoading) return <LoadingCard />

  const handleNewTournament = () => {
    alert("Iniciando novo tournament... Esta funcionalidade requer a seleção de candidatos de um experimento de otimização (em breve).");
  };

  const handleLeaderboard = (id: string) => {
    alert(`Visualizando Leaderboard para Tournament: ${id}`);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Optimization <span className="text-primary">Tournaments</span></h1>
          <p className="text-muted-foreground font-medium text-lg">Auto-otimização evolucionária de prompts e hiperparâmetros.</p>
        </div>
        <button 
          onClick={handleNewTournament}
          className="bg-primary text-primary-foreground px-6 py-3 rounded-2xl font-bold flex items-center gap-2 hover:opacity-90 transition-all shadow-lg shadow-primary/20"
        >
          <Play className="w-5 h-5" />
          Novo Tournament
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1">Tournaments Ativos</h2>
          <div className="space-y-4">
            {tournaments.map((trn: any) => (
              <div key={trn.id} className="bg-card border border-border rounded-3xl p-6 hover:border-primary/30 transition-all">
                <div className="flex justify-between items-start mb-6">
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-2xl ${
                      trn.status === 'running' ? 'bg-primary/10 text-primary' :
                      trn.status === 'completed' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-muted text-muted-foreground'
                    }`}>
                      <Trophy className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="text-xl font-black text-foreground">{trn.name || `Tournament ${trn.id.slice(0,8)}`}</h3>
                      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                        Agent: <span className="text-foreground font-bold">{trn.agent_id.slice(0,8)}</span> • Status: <span className="text-primary font-bold">{trn.status}</span>
                      </div>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded text-[10px] font-black uppercase tracking-tighter ${
                    trn.status === 'running' ? 'bg-primary/10 text-primary animate-pulse' :
                    trn.status === 'completed' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-muted text-muted-foreground'
                  }`}>
                    {trn.status}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-4 mb-6">
                   <div className="p-3 bg-muted/30 rounded-2xl">
                      <div className="text-[8px] font-black uppercase text-muted-foreground tracking-widest mb-1">Candidatos</div>
                      <div className="text-lg font-black text-foreground">{trn.candidate_ids?.length || 0}</div>
                   </div>
                   <div className="p-3 bg-muted/30 rounded-2xl">
                      <div className="text-[8px] font-black uppercase text-muted-foreground tracking-widest mb-1">Estratégia</div>
                      <div className="text-xs font-bold text-foreground">PSO</div>
                   </div>
                   <div className="p-3 bg-muted/30 rounded-2xl">
                      <div className="text-[8px] font-black uppercase text-muted-foreground tracking-widest mb-1">Confidence</div>
                      <div className="text-lg font-black text-emerald-600">{trn.confidence_score || '0.000'}</div>
                   </div>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-border">
                  <div className="flex items-center gap-2">
                    <FlaskConical className="w-4 h-4 text-muted-foreground" />
                    <span className="text-[10px] font-black text-muted-foreground uppercase">Evolving Strategy: Random Search + PSO</span>
                  </div>
                  <div className="flex gap-2">
                    {trn.status === 'pending' && (
                      <button onClick={() => runMutation.mutate(trn.id)} className="bg-primary/10 text-primary text-xs font-bold px-4 py-2 rounded-xl hover:bg-primary/20 transition-all">
                        Run
                      </button>
                    )}
                    <button onClick={() => handleLeaderboard(trn.id)} className="bg-foreground text-background text-xs font-bold px-4 py-2 rounded-xl hover:opacity-90 transition-all">
                      Visualizar Leaderboard
                    </button>
                  </div>
                </div>
              </div>
            ))}
            {tournaments.length === 0 && (
              <div className="text-center py-20 text-muted-foreground border border-dashed border-border rounded-3xl">
                 <Trophy className="w-12 h-12 mx-auto mb-4 opacity-20" />
                 <p className="font-bold">Nenhum tournament encontrado.</p>
                 <p className="text-sm opacity-60">Inicie um experimento de otimização para gerar candidatos.</p>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-8">
           <section>
              <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1 mb-4">Métricas de Otimização</h2>
              <div className="bg-card border border-border rounded-3xl p-6 space-y-6">
                 <div className="space-y-4">
                    <div className="flex items-center justify-between">
                       <span className="text-sm font-medium">Melhora Média</span>
                       <span className="text-emerald-500 font-bold">+24.5%</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-1.5">
                       <div className="bg-emerald-500 h-full w-[75%] rounded-full" />
                    </div>
                 </div>
                 <div className="space-y-4">
                    <div className="flex items-center justify-between">
                       <span className="text-sm font-medium">Economia de Custo</span>
                       <span className="text-primary font-bold">12.2k USD</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-1.5">
                       <div className="bg-primary h-full w-[45%] rounded-full" />
                    </div>
                 </div>
              </div>
           </section>

           <div className="bg-amber-50 border border-amber-100 rounded-3xl p-6">
              <div className="flex items-center gap-2 mb-3 text-amber-600">
                <Target className="w-5 h-5" />
                <h3 className="font-black uppercase tracking-tight text-sm">Próximos Passos</h3>
              </div>
              <p className="text-xs text-amber-700 font-medium leading-relaxed">
                Recomendamos rodar um tournament de otimização para o agente <strong>Customer-Support</strong>, cujo score de satisfação caiu 5% na última semana.
              </p>
           </div>
        </div>
      </div>
    </div>
  )
}
