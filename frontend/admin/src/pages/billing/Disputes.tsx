import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Gavel, TrendingUp, Filter, Search, MoreHorizontal, AlertCircle } from 'lucide-react'
import api from '../../lib/api'

export default function Disputes() {
  const [query, setQuery] = useState('')
  const { data: disputes = [] } = useQuery({
    queryKey: ['billing-disputes'],
    queryFn: () => api.listBillingDisputes(),
  })
  const filteredDisputes = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return disputes
    return disputes.filter((dispute: any) => {
      const client = String(dispute.client_name || dispute.client || '').toLowerCase()
      const id = String(dispute.id || '').toLowerCase()
      const reason = String(dispute.reason || '').toLowerCase()
      return client.includes(normalized) || id.includes(normalized) || reason.includes(normalized)
    })
  }, [disputes, query])
  const summary = filteredDisputes.reduce(
    (acc: Record<string, number>, dispute: any) => {
      const status = String(dispute.status || 'pending')
      acc[status] = (acc[status] || 0) + 1
      return acc
    },
    {},
  )

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
                <span className="font-bold text-amber-600">{summary.pending || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Em Revisão</span>
                <span className="font-bold text-primary">{summary.under_review || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Resolvidas (30d)</span>
                <span className="font-bold text-emerald-600">{summary.resolved || 0}</span>
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
                <input
                  type="text"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Buscar por cliente ou ID da disputa..."
                  className="flex-1 bg-transparent border-none outline-none text-sm"
                />
             </div>
             <div className="divide-y divide-border">
                {filteredDisputes.map((dispute: any) => (
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
                              <h3 className="text-lg font-black text-foreground">{dispute.client_name || dispute.client || 'Cliente'}</h3>
                              <span className="text-[10px] font-mono text-muted-foreground">{dispute.id}</span>
                           </div>
                           <p className="text-sm text-muted-foreground font-medium mb-3">{dispute.reason}</p>
                           <div className="flex items-center gap-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                              <span>{new Date(dispute.created_at || dispute.date || Date.now()).toLocaleDateString()}</span>
                              <span className="flex items-center gap-1.5">
                                 <TrendingUp className="w-3 h-3" />
                                 {typeof dispute.amount_brl === 'number' ? `R$ ${dispute.amount_brl.toFixed(2)}` : dispute.amount || 'R$ 0,00'}
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
                {filteredDisputes.length === 0 && (
                  <div className="p-8 text-sm text-muted-foreground">Nenhuma disputa encontrada.</div>
                )}
             </div>
          </div>
        </div>
      </div>
    </div>
  )
}
