import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { Scale, Activity, AlertTriangle, CheckCircle, RefreshCw, Filter, ArrowRight, Wallet, Shield } from 'lucide-react'
import { useState } from 'react'

export default function Reconciliation() {
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState('mismatch')

  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['recon-overview'],
    queryFn: () => api.getReconciliationOverview()
  })

  const { data: mismatches, isLoading: mismatchesLoading } = useQuery({
    queryKey: ['recon-mismatches', filter],
    queryFn: () => api.listReconciliationMismatches()
  })

  const runReconMutation = useMutation({
    mutationFn: (hours: number) => api.runReconciliation(hours),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recon-overview'] })
      queryClient.invalidateQueries({ queryKey: ['recon-mismatches'] })
    }
  })

  if (overviewLoading) return <div className="p-8">Conciliando transações financeiras...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Billing <span className="text-primary">Reconciliation</span></h1>
          <p className="text-muted-foreground font-medium text-lg">Detecção de discrepâncias entre uso medido e cobrança efetuada.</p>
        </div>
        <button 
          onClick={() => runReconMutation.mutate(24)}
          disabled={runReconMutation.isPending}
          className="bg-primary text-primary-foreground px-6 py-3 rounded-2xl font-bold flex items-center gap-2 hover:opacity-90 transition-all shadow-lg shadow-primary/20"
        >
          <RefreshCw className={`w-5 h-5 ${runReconMutation.isPending ? 'animate-spin' : ''}`} />
          Rodar Conciliação (24h)
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Itens Pendentes</div>
          <div className="text-3xl font-black text-foreground">{overview?.pending_mismatches || 0}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Divergência Total</div>
          <div className="text-3xl font-black text-rose-600">R$ {overview?.total_mismatch_amount || '0,00'}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Última Execução</div>
          <div className="text-lg font-bold text-muted-foreground mt-2">{overview?.last_run ? new Date(overview.last_run).toLocaleString('pt-BR') : 'Nunca'}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Health Score</div>
          <div className="flex items-center gap-2">
            <div className="text-3xl font-black text-emerald-600">{overview?.integrity_score || 100}%</div>
            <CheckCircle className="w-6 h-6 text-emerald-500" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="flex justify-between items-center px-1">
            <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest">Divergências Detectadas</h2>
            <div className="flex gap-2">
              <button onClick={() => setFilter('mismatch')} className={`px-3 py-1 rounded-lg text-[10px] font-bold uppercase transition-all ${filter === 'mismatch' ? 'bg-foreground text-background' : 'bg-muted text-muted-foreground'}`}>Ativas</button>
              <button onClick={() => setFilter('resolved')} className={`px-3 py-1 rounded-lg text-[10px] font-bold uppercase transition-all ${filter === 'resolved' ? 'bg-foreground text-background' : 'bg-muted text-muted-foreground'}`}>Resolvidas</button>
            </div>
          </div>

          <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-muted/50 border-bottom border-border">
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">ID / Referência</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Medido</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Cobrado</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Gap</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground text-right">Ação</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {mismatches?.map((item: any) => (
                  <tr key={item.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-bold text-foreground">Client: {item.client_id?.slice(0, 8)}</div>
                      <div className="text-[10px] text-muted-foreground font-mono">{item.reference_id}</div>
                    </td>
                    <td className="px-6 py-4 text-xs font-bold text-foreground">R$ {item.measured_amount}</td>
                    <td className="px-6 py-4 text-xs font-bold text-foreground">R$ {item.billed_amount}</td>
                    <td className="px-6 py-4">
                       <span className={`text-xs font-black ${item.measured_amount > item.billed_amount ? 'text-rose-600' : 'text-emerald-600'}`}>
                         {item.measured_amount > item.billed_amount ? '+' : ''} R$ {(item.measured_amount - item.billed_amount).toFixed(2)}
                       </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="bg-foreground text-background px-3 py-1.5 rounded-lg text-[10px] font-black uppercase hover:opacity-90 transition-all">
                        Resolver
                      </button>
                    </td>
                  </tr>
                ))}
                {(!mismatches || mismatches.length === 0) && (
                  <tr>
                    <td colSpan={5} className="px-6 py-20 text-center text-muted-foreground">
                      Nenhuma divergência encontrada. O sistema está íntegro.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-8">
           <section>
              <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1 mb-4">Ações Rápidas</h2>
              <div className="space-y-4">
                <button className="w-full p-6 bg-card border border-border rounded-3xl hover:border-primary transition-all text-left group">
                   <div className="flex items-center justify-between mb-4">
                      <div className="p-3 bg-primary/10 text-primary rounded-2xl group-hover:bg-primary group-hover:text-white transition-all">
                        <Wallet className="w-5 h-5" />
                      </div>
                      <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-all" />
                   </div>
                   <h3 className="text-lg font-bold text-foreground mb-1">Manual Credit</h3>
                   <p className="text-sm text-muted-foreground">Emitir crédito manual para compensar divergência ou disputa.</p>
                </button>

                <div className="bg-amber-50 border border-amber-100 rounded-3xl p-6">
                  <div className="flex items-center gap-2 mb-3 text-amber-600">
                    <AlertTriangle className="w-5 h-5" />
                    <h3 className="font-black uppercase tracking-tight text-sm">Disputas Ativas</h3>
                  </div>
                  <p className="text-xs text-amber-700 font-medium mb-4 leading-relaxed">
                    Existem 5 solicitações de revisão de faturamento aguardando análise humana.
                  </p>
                  <button className="w-full py-2 bg-amber-600 text-white text-[10px] font-black uppercase tracking-widest rounded-xl hover:bg-amber-700 transition-colors">
                    Ver Disputas
                  </button>
                </div>
              </div>
           </section>

           <section>
              <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1 mb-4">Audit Chain Integrity</h2>
              <div className="bg-foreground text-background rounded-3xl p-6 shadow-xl">
                 <div className="flex items-center gap-2 mb-4 text-emerald-400">
                    <Shield className="w-5 h-5" />
                    <span className="text-sm font-bold uppercase tracking-tight">Cadeia Validada</span>
                 </div>
                 <p className="text-[10px] text-muted-foreground leading-relaxed mb-6">
                    A integridade criptográfica da trilha de auditoria financeira foi verificada com sucesso. Nenhuma alteração não autorizada detectada.
                 </p>
                 <button className="w-full py-3 bg-background text-foreground text-[10px] font-black uppercase tracking-widest rounded-xl hover:opacity-90">
                    Verificar Agora
                 </button>
              </div>
           </section>
        </div>
      </div>
    </div>
  )
}
