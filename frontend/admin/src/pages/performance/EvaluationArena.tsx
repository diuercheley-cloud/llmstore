import { useQuery, useMutation } from '@tanstack/react-query'
import api from '../../lib/api'
import { Trophy, Swords, ShieldAlert, Activity, BarChart3, Play, History, CheckCircle2, AlertCircle, Info, TrendingUp, Search } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

export default function EvaluationArena() {
  const [activeTab, setActiveTab] = useState('rankings')

  const { data: rankings, isLoading: isLoadingRankings } = useQuery({
    queryKey: ['evaluation-rankings'],
    queryFn: async () => {
      const res = await api.get('/admin/evaluation/rankings')
      return res.data
    }
  })

  const { data: findings, isLoading: isLoadingFindings } = useQuery({
    queryKey: ['red-team-findings'],
    queryFn: async () => {
      const res = await api.get('/admin/evaluation/red-team/findings')
      return res.data
    }
  })

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-foreground flex items-center gap-3">
            <Trophy className="w-8 h-8 text-primary" /> EVALUATION ARENA
          </h1>
          <p className="text-muted-foreground mt-1">Ranking contínuo, benchmarking e auditoria de segurança (Red-Teaming).</p>
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-secondary text-foreground rounded-xl font-bold text-sm">
            <History className="w-4 h-4" /> Histórico
          </button>
          <button className="flex items-center gap-2 px-6 py-2 bg-primary text-primary-foreground rounded-xl font-black text-sm shadow-lg shadow-primary/20">
            <Play className="w-4 h-4" /> NOVA AVALIAÇÃO
          </button>
        </div>
      </div>

      <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
        <div className="flex border-b border-border bg-secondary/10">
          <button 
            onClick={() => setActiveTab('rankings')}
            className={`px-8 py-4 text-sm font-black tracking-tighter border-b-2 transition-all ${activeTab === 'rankings' ? 'border-primary text-primary bg-primary/5' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
          >
            ELO RANKINGS
          </button>
          <button 
            onClick={() => setActiveTab('redteam')}
            className={`px-8 py-4 text-sm font-black tracking-tighter border-b-2 transition-all ${activeTab === 'redteam' ? 'border-primary text-primary bg-primary/5' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
          >
            RED-TEAM FINDINGS
          </button>
        </div>

        <div className="p-6">
          {activeTab === 'rankings' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {rankings?.slice(0, 4).map((r: any, idx: number) => (
                  <div key={r.name} className="p-5 bg-secondary/20 border border-border rounded-2xl relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-3 opacity-10">
                      <TrendingUp className="w-12 h-12" />
                    </div>
                    <div className="text-[10px] font-black text-muted-foreground uppercase mb-1">Rank #{idx + 1}</div>
                    <div className="font-black text-lg truncate mb-2">{r.name}</div>
                    <div className="flex items-end gap-2">
                      <div className="text-2xl font-black text-primary">{r.rating}</div>
                      <div className="text-[10px] font-bold text-muted-foreground pb-1">ELO</div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="border border-border rounded-2xl overflow-hidden">
                <table className="w-full text-left text-sm">
                  <thead className="bg-secondary/30 text-[10px] font-black uppercase text-muted-foreground tracking-widest border-b border-border">
                    <tr>
                      <th className="px-6 py-3">Modelo / Agente</th>
                      <th className="px-6 py-3">ELO Rating</th>
                      <th className="px-6 py-3 text-center">Partidas</th>
                      <th className="px-6 py-3 text-right">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {rankings?.map((r: any) => (
                      <tr key={r.name} className="hover:bg-secondary/10 transition-colors">
                        <td className="px-6 py-4 font-bold">{r.name}</td>
                        <td className="px-6 py-4 font-mono font-black text-primary">{r.rating}</td>
                        <td className="px-6 py-4 text-center font-medium">{r.matches}</td>
                        <td className="px-6 py-4 text-right">
                          <button className="text-[10px] font-black uppercase text-primary hover:underline">Ver Detalhes</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'redteam' && (
            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input 
                    type="text" 
                    placeholder="Filtrar findings..." 
                    className="w-full bg-background border border-border rounded-xl pl-10 pr-4 py-2 text-sm outline-none focus:ring-2 ring-primary/20"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4">
                {findings?.map((f: any) => (
                  <div key={f.id} className={`p-5 border rounded-2xl flex items-start gap-4 transition-all hover:scale-[1.005] ${f.severity === 'high' ? 'bg-destructive/5 border-destructive/20' : 'bg-secondary/20 border-border'}`}>
                    <div className={`p-3 rounded-xl ${f.severity === 'high' ? 'bg-destructive/10 text-destructive' : 'bg-primary/10 text-primary'}`}>
                      <ShieldAlert className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-[10px] font-black uppercase tracking-widest">{f.finding_type.replace('_', ' ')}</span>
                        <span className={`text-[9px] font-black px-2 py-0.5 rounded uppercase ${f.severity === 'high' ? 'bg-destructive text-destructive-foreground' : 'bg-secondary text-muted-foreground'}`}>
                          {f.severity}
                        </span>
                      </div>
                      <h3 className="font-bold text-sm mb-2">{f.description}</h3>
                      <div className="bg-background/50 p-3 rounded-lg font-mono text-[10px] text-muted-foreground border border-border/50">
                        Payload: {f.payload_used}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
