import { Gavel, TrendingUp, Filter, Search, MoreHorizontal, User, AlertCircle, CheckCircle } from 'lucide-react'

export default function Disputes() {
  const disputes = [
    { id: 'disp-101', client: 'Acme Corp', amount: 'R$ 1.250,00', status: 'pending', date: '2026-05-30', reason: 'Diferença de tokens medidos no modelo Llama-3' },
    { id: 'disp-102', client: 'Global Systems', amount: 'R$ 450,00', status: 'under_review', date: '2026-05-29', reason: 'Cobrança duplicada em 15/05' },
    { id: 'disp-103', client: 'Start-UP Tech', amount: 'R$ 2.100,00', status: 'resolved', date: '2026-05-28', reason: 'Ajuste de camada de precificação' },
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Billing <span className="text-primary">Disputes</span></h1>
          <p className="text-muted-foreground font-medium text-lg">Central de mediação e resolução de divergências financeiras.</p>
        </div>
        <button className="bg-card border border-border px-6 py-3 rounded-2xl font-bold flex items-center gap-2 hover:bg-muted transition-all">
          <Filter className="w-5 h-5" />
          Filtros Avançados
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-card border border-border rounded-3xl p-6">
            <h3 className="text-xs font-black text-muted-foreground uppercase tracking-widest mb-4">Resumo</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Aguardando</span>
                <span className="font-bold text-amber-600">5</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Em Revisão</span>
                <span className="font-bold text-primary">2</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Resolvidas (30d)</span>
                <span className="font-bold text-emerald-600">24</span>
              </div>
            </div>
          </div>

          <div className="bg-amber-50 border border-amber-100 rounded-3xl p-6">
            <div className="flex items-center gap-2 mb-3 text-amber-600">
              <AlertCircle className="w-5 h-5" />
              <h3 className="font-black uppercase tracking-tight text-sm">Atenção</h3>
            </div>
            <p className="text-xs text-amber-700 font-medium leading-relaxed">
              O tempo médio de resolução aumentou 15% esta semana. Recomenda-se priorizar tickets críticos.
            </p>
          </div>
        </div>

        <div className="lg:col-span-3 space-y-6">
          <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
             <div className="p-4 border-b border-border flex items-center gap-4">
                <Search className="w-5 h-5 text-muted-foreground" />
                <input type="text" placeholder="Buscar por cliente ou ID da disputa..." className="flex-1 bg-transparent border-none outline-none text-sm" />
             </div>
             <div className="divide-y divide-border">
                {disputes.map(dispute => (
                  <div key={dispute.id} className="p-6 hover:bg-muted/30 transition-all flex items-start justify-between">
                     <div className="flex items-start gap-4">
                        <div className={`p-3 rounded-2xl ${
                          dispute.status === 'pending' ? 'bg-amber-500/10 text-amber-600' :
                          dispute.status === 'under_review' ? 'bg-primary/10 text-primary' : 'bg-emerald-500/10 text-emerald-600'
                        }`}>
                           <Gavel className="w-6 h-6" />
                        </div>
                        <div>
                           <div className="flex items-center gap-2 mb-1">
                              <h3 className="text-lg font-black text-foreground">{dispute.client}</h3>
                              <span className="text-[10px] font-mono text-muted-foreground">{dispute.id}</span>
                           </div>
                           <p className="text-sm text-muted-foreground font-medium mb-3">{dispute.reason}</p>
                           <div className="flex items-center gap-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                              <span>{dispute.date}</span>
                              <span className="flex items-center gap-1.5">
                                 <TrendingUp className="w-3 h-3" />
                                 {dispute.amount}
                              </span>
                           </div>
                        </div>
                     </div>
                     <div className="flex flex-col items-end gap-3">
                        <span className={`px-2 py-1 rounded text-[10px] font-black uppercase tracking-tighter ${
                          dispute.status === 'pending' ? 'bg-amber-500/10 text-amber-600' :
                          dispute.status === 'under_review' ? 'bg-primary/10 text-primary' : 'bg-emerald-500/10 text-emerald-600'
                        }`}>
                           {dispute.status.replace('_', ' ')}
                        </span>
                        <button className="p-2 hover:bg-muted rounded-xl transition-all">
                           <MoreHorizontal className="w-5 h-5 text-muted-foreground" />
                        </button>
                     </div>
                  </div>
                ))}
             </div>
          </div>
        </div>
      </div>
    </div>
  )
}
