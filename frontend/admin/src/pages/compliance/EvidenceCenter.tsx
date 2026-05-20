import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { FileText, RefreshCw, Download, CheckCircle2, ChevronLeft, Search, Lock } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function EvidenceCenter() {
  const queryClient = useQueryClient()
  const { data: index, isLoading } = useQuery({
    queryKey: ['compliance-evidence-latest'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/evidence/latest')
      return res.data
    }
  })

  const mutation = useMutation({
    mutationFn: async () => {
      return api.post('/admin/compliance/evidence/collect-all')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-evidence-latest'] })
    }
  })

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div>
          <Link to="/compliance" className="text-slate-400 hover:text-emerald-600 transition-colors flex items-center gap-1 text-[10px] font-black uppercase tracking-widest mb-4">
             <ChevronLeft className="w-3 h-3" /> Back to Readiness
          </Link>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Evidence <span className="text-emerald-600">Center</span></h1>
          <p className="text-slate-500 font-medium text-lg">Repositório central de evidências técnicas sanitizadas.</p>
        </div>
        <div className="flex gap-4">
           <button 
             onClick={() => mutation.mutate()}
             disabled={mutation.isPending}
             className="flex items-center gap-2 bg-slate-900 text-white px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-emerald-600 transition-all shadow-xl shadow-slate-200 disabled:opacity-50"
           >
             <RefreshCw className={`w-4 h-4 ${mutation.isPending ? 'animate-spin' : ''}`} />
             {mutation.isPending ? 'Collecting...' : 'Refresh Evidence'}
           </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
         <div className="lg:col-span-2">
            <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden">
               <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                  <div className="flex items-center gap-2">
                     <Search className="w-4 h-4 text-slate-400" />
                     <input type="text" placeholder="Search evidence..." className="bg-transparent text-xs font-medium focus:outline-none w-64" />
                  </div>
                  <div className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                     {index?.length || 0} Items Indexed
                  </div>
               </div>

               <div className="divide-y divide-slate-100">
                  {index?.map((item: any, i: number) => (
                    <div key={i} className="p-6 hover:bg-slate-50/50 transition-all group flex justify-between items-center">
                       <div className="flex items-start gap-4">
                          <div className="p-3 bg-slate-100 text-slate-500 rounded-xl group-hover:bg-emerald-50 group-hover:text-emerald-600 transition-colors">
                             <FileText className="w-5 h-5" />
                          </div>
                          <div>
                             <h4 className="text-sm font-black text-slate-900 uppercase tracking-tight">{item.source}</h4>
                             <p className="text-[10px] text-slate-400 font-medium mt-1 truncate max-w-xs">{item.original_path}</p>
                             <div className="flex items-center gap-2 mt-2">
                                <span className="text-[8px] font-mono text-slate-300 bg-slate-100 px-2 py-0.5 rounded uppercase">{item.hash_sha256.substring(0, 16)}...</span>
                                <span className="text-[8px] font-black uppercase tracking-widest text-emerald-500 flex items-center gap-1">
                                   <CheckCircle2 className="w-2 h-2" /> Verified
                                </span>
                             </div>
                          </div>
                       </div>
                       <div className="flex items-center gap-3">
                          <button className="p-2 text-slate-400 hover:text-emerald-600 transition-colors bg-white border border-slate-100 rounded-lg shadow-sm">
                             <Download className="w-4 h-4" />
                          </button>
                       </div>
                    </div>
                  ))}
                  {index?.length === 0 && (
                    <div className="p-20 text-center text-slate-400 font-black uppercase tracking-widest">
                       Nenhuma evidência coletada. Clique em "Refresh Evidence".
                    </div>
                  )}
               </div>
            </div>
         </div>

         <div className="space-y-6">
            <div className="bg-emerald-900 text-white rounded-3xl p-8 relative overflow-hidden">
               <Lock className="w-24 h-24 absolute -bottom-6 -right-6 text-emerald-800/50" />
               <h3 className="text-lg font-black mb-2 relative z-10">Data Sanitization</h3>
               <p className="text-sm text-emerald-100/70 mb-6 font-medium relative z-10 leading-relaxed">
                  Todas as evidências são automaticamente sanitizadas. Segredos e tokens são removidos antes do armazenamento.
               </p>
               <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-emerald-400 relative z-10">
                  <CheckCircle2 className="w-4 h-4" /> PII Masking Active
               </div>
            </div>

            <div className="bg-slate-50 border border-slate-100 rounded-3xl p-6">
               <h4 className="text-[10px] font-black uppercase text-slate-400 mb-4 tracking-widest">Evidence Policies</h4>
               <div className="space-y-4">
                  <div className="flex items-center gap-3">
                     <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></div>
                     <p className="text-[10px] text-slate-600 font-bold uppercase tracking-tight">Retenção de 90 dias ativa</p>
                  </div>
                  <div className="flex items-center gap-3">
                     <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></div>
                     <p className="text-[10px] text-slate-600 font-bold uppercase tracking-tight">Imutabilidade garantida via Hash</p>
                  </div>
                  <div className="flex items-center gap-3">
                     <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></div>
                     <p className="text-[10px] text-slate-600 font-bold uppercase tracking-tight">Acesso auditado (RBAC)</p>
                  </div>
               </div>
            </div>
         </div>
      </div>
    </div>
  )
}
