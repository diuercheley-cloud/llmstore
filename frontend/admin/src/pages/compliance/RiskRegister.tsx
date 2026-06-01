import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import { AlertTriangle, ChevronLeft, ShieldAlert, BarChart, Plus } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function RiskRegister() {
  const { data: riskData, isLoading } = useQuery({
    queryKey: ['compliance-risk-register'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/isms/risk-register')
      return res.data
    }
  })

  const getRiskColor = (score: number) => {
    if (score >= 15) return 'text-destructive bg-destructive/10 border-rose-100'
    if (score >= 10) return 'text-yellow-600 bg-yellow-500/10 border-amber-100'
    return 'text-emerald-600 bg-emerald-50 border-emerald-100'
  }

  const risks = riskData?.risks || []
  const highSeverityCount = risks.filter((risk: any) => Number(risk.score ?? 0) >= 15).length
  const mitigatedCount = risks.filter((risk: any) => risk.status && risk.status !== 'active').length
  const mitigatedRate = risks.length ? Math.round((mitigatedCount / risks.length) * 100) : 0
  const residualScore = risks.length ? (risks.reduce((sum: number, risk: any) => sum + Number(risk.score ?? 0), 0) / risks.length) : 0

  const getRiskStatusLabel = (value: string) => {
    if (value === 'active') return 'Ativo'
    return 'Mitigado'
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div>
          <Link to="/compliance" className="text-muted-foreground hover:text-emerald-600 transition-colors flex items-center gap-1 text-[10px] font-black uppercase tracking-widest mb-4">
             <ChevronLeft className="w-3 h-3" /> Voltar ao resumo
          </Link>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Registro de <span className="text-destructive">riscos</span></h1>
          <p className="text-muted-foreground font-medium text-lg">Inventário de riscos de segurança e planos de tratamento.</p>
        </div>
        <button className="flex items-center gap-2 bg-foreground text-background px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-destructive transition-all shadow-xl shadow-slate-200">
           <Plus className="w-4 h-4" /> Cadastrar risco
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-10">
         <div className="bg-card border border-border rounded-3xl p-6 min-h-[140px] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Total de riscos</div>
            <div className="text-3xl font-black text-foreground">{risks.length}</div>
         </div>
         <div className="bg-destructive/10 border border-rose-100 rounded-3xl p-6 min-h-[140px] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <div className="text-[10px] font-black uppercase tracking-widest text-destructive mb-2">Alta severidade</div>
            <div className="text-3xl font-black text-destructive">{highSeverityCount}</div>
         </div>
         <div className="bg-emerald-50 border border-emerald-100 rounded-3xl p-6 min-h-[140px] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <div className="text-[10px] font-black uppercase tracking-widest text-emerald-400 mb-2">Mitigados</div>
            <div className="text-3xl font-black text-emerald-600">{mitigatedRate}%</div>
         </div>
         <div className="bg-foreground rounded-3xl p-6 min-h-[140px] text-background flex items-center justify-between transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl">
            <div>
               <div className="text-muted-foreground text-[10px] font-black uppercase tracking-widest mb-2">Score residual</div>
               <div className="text-3xl font-black">{residualScore.toFixed(1)}</div>
            </div>
            <BarChart className="w-8 h-8 text-emerald-500" />
         </div>
      </div>

      <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm transition-all duration-200 hover:shadow-lg">
         <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
               <thead>
                  <tr className="bg-secondary/50 text-[10px] font-black uppercase tracking-widest text-muted-foreground border-b border-border">
                     <th className="px-8 py-4">ID</th>
                     <th className="px-8 py-4">Descrição do risco</th>
                     <th className="px-8 py-4 text-center">Score inerente</th>
                     <th className="px-8 py-4">Plano de tratamento</th>
                     <th className="px-8 py-4">Status</th>
                  </tr>
               </thead>
               <tbody className="divide-y divide-border">
                  {risks.map((risk: any) => (
                    <tr key={risk.id} className="hover:bg-secondary/50 transition-colors duration-150 group">
                       <td className="px-8 py-6 font-mono text-xs text-muted-foreground">{risk.id}</td>
                       <td className="px-8 py-6 max-w-xs">
                          <div className="font-bold text-foreground text-sm mb-1">{risk.title}</div>
                          <div className="text-[10px] text-muted-foreground font-medium leading-relaxed">{risk.description}</div>
                       </td>
                       <td className="px-8 py-6 text-center">
                          <div className={`inline-flex items-center justify-center w-10 h-10 rounded-xl border text-sm font-black ${getRiskColor(risk.score)}`}>
                             {risk.score}
                          </div>
                       </td>
                       <td className="px-8 py-6">
                          <div className="p-3 bg-secondary rounded-xl border border-border text-[10px] font-medium text-muted-foreground leading-relaxed">
                             {risk.treatment_plan}
                          </div>
                       </td>
                       <td className="px-8 py-6">
                          <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${
                             risk.status === 'active' ? 'bg-yellow-500/10 text-yellow-600' : 'bg-emerald-50 text-emerald-600'
                          }`}>
                             {getRiskStatusLabel(risk.status)}
                          </span>
                       </td>
                    </tr>
                  ))}
                  {risks.length === 0 && (
                    <tr>
                      <td className="px-8 py-10 text-center text-muted-foreground" colSpan={5}>
                        Nenhum risco encontrado.
                      </td>
                    </tr>
                  )}
               </tbody>
            </table>
         </div>
      </div>
    </div>
  )
}
