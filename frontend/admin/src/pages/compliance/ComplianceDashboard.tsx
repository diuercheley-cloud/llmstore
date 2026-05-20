import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import { ShieldCheck, FileCheck, AlertCircle, BarChart3, BookOpen, Clock, ChevronRight } from 'lucide-react'

export default function ComplianceDashboard() {
  const { data: frameworks, isLoading } = useQuery({
    queryKey: ['compliance-frameworks'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/frameworks')
      return res.data
    }
  })

  if (isLoading) return <div className="p-8 font-black uppercase text-slate-400">Analisando Prontidão...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Compliance <span className="text-emerald-600">Readiness</span></h1>
          <p className="text-slate-500 font-medium text-lg">Preparação para auditorias SOC 2 e ISO 27001.</p>
        </div>
        <div className="flex gap-4">
           <div className="flex items-center gap-2 bg-emerald-50 text-emerald-700 px-4 py-2 rounded-2xl border border-emerald-100">
             <ShieldCheck className="w-4 h-4" />
             <span className="text-xs font-black uppercase tracking-widest">Audit Ready: 45%</span>
           </div>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {frameworks?.map((fw: any) => (
              <div key={fw.id} className="bg-white border border-slate-200 rounded-3xl p-8 hover:border-emerald-300 transition-all group">
                <div className="flex justify-between items-start mb-6">
                  <div className="p-3 bg-emerald-50 text-emerald-600 rounded-2xl group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                    <FileCheck className="w-6 h-6" />
                  </div>
                  <span className="bg-slate-100 text-slate-500 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-tighter">
                    v{fw.version}
                  </span>
                </div>
                <h3 className="text-2xl font-black text-slate-900 mb-2">{fw.name}</h3>
                <p className="text-sm text-slate-500 mb-8 font-medium leading-relaxed">{fw.description}</p>
                
                <div className="space-y-4">
                   <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: '45%' }}></div>
                   </div>
                   <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-slate-400">
                      <span>Prontidão</span>
                      <span className="text-emerald-600">45% Complete</span>
                   </div>
                </div>

                <button className="w-full mt-8 py-3 rounded-2xl bg-slate-900 text-white text-[10px] font-black uppercase tracking-widest hover:bg-emerald-600 transition-colors flex items-center justify-center gap-2">
                   Ver Controles <ChevronRight className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>

          <div className="bg-slate-900 text-white rounded-3xl p-8">
             <div className="flex items-center gap-3 mb-6">
                <BarChart3 className="w-6 h-6 text-emerald-400" />
                <h2 className="text-xl font-black uppercase tracking-tight">Executive Summary</h2>
             </div>
             <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                <div className="p-6 rounded-2xl bg-slate-800/50 border border-slate-700">
                   <div className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-2">Controles Totais</div>
                   <div className="text-3xl font-black">158</div>
                </div>
                <div className="p-6 rounded-2xl bg-slate-800/50 border border-slate-700">
                   <div className="text-emerald-400 text-[10px] font-black uppercase tracking-widest mb-2">Implementados</div>
                   <div className="text-3xl font-black text-emerald-400">72</div>
                </div>
                <div className="p-6 rounded-2xl bg-slate-800/50 border border-slate-700">
                   <div className="text-amber-400 text-[10px] font-black uppercase tracking-widest mb-2">Gaps Ativos</div>
                   <div className="text-3xl font-black text-amber-400">86</div>
                </div>
             </div>
          </div>
        </div>

        <div className="space-y-6">
           <div className="bg-white border border-slate-200 rounded-3xl p-6">
              <div className="flex items-center gap-2 mb-6 text-slate-900">
                <Clock className="w-5 h-5 text-emerald-600" />
                <h3 className="font-black uppercase tracking-tight text-sm">Próximas Evidências</h3>
              </div>
              <div className="space-y-4">
                 {[
                   { t: 'Revisão de Acesso Trimestral', d: 'In 4 days' },
                   { t: 'Teste de Penetração Anual', d: 'In 12 days' },
                   { t: 'Backup Restore Validation', d: 'In 15 days' }
                 ].map((item, i) => (
                   <div key={i} className="flex justify-between items-center p-3 rounded-xl hover:bg-slate-50 transition-colors">
                      <div>
                         <div className="font-bold text-xs">{item.t}</div>
                         <div className="text-[10px] text-slate-400">{item.d}</div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-300" />
                   </div>
                 ))}
              </div>
           </div>

           <div className="bg-emerald-900 text-white rounded-3xl p-8 relative overflow-hidden">
              <BookOpen className="w-24 h-24 absolute -bottom-6 -right-6 text-emerald-800/50" />
              <h3 className="text-lg font-black mb-2 relative z-10">Políticas de Segurança</h3>
              <p className="text-sm text-emerald-100/70 mb-6 font-medium relative z-10 leading-relaxed">
                Acesse o repositório central de políticas aprovadas para ISO 27001.
              </p>
              <button className="bg-white text-emerald-900 px-6 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest hover:bg-emerald-50 transition-colors relative z-10">
                Ver Políticas
              </button>
           </div>

           <div className="p-6 bg-slate-50 rounded-3xl border border-slate-100">
              <div className="flex items-start gap-3">
                 <AlertCircle className="w-5 h-5 text-slate-400 mt-0.5" />
                 <div>
                    <h4 className="text-xs font-black uppercase text-slate-900 mb-1">Nota Legal</h4>
                    <p className="text-[10px] text-slate-500 font-medium leading-relaxed">
                       Este módulo fornece ferramentas para prontidão e auditoria interna. O uso não constitui uma certificação formal.
                    </p>
                 </div>
              </div>
           </div>
        </div>
      </div>
    </div>
  )
}
