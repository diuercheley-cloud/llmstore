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
    if (score >= 15) return 'text-rose-600 bg-rose-50 border-rose-100'
    if (score >= 10) return 'text-amber-600 bg-amber-50 border-amber-100'
    return 'text-emerald-600 bg-emerald-50 border-emerald-100'
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div>
          <Link to="/compliance" className="text-slate-400 hover:text-emerald-600 transition-colors flex items-center gap-1 text-[10px] font-black uppercase tracking-widest mb-4">
             <ChevronLeft className="w-3 h-3" /> Back to Readiness
          </Link>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Risk <span className="text-rose-600">Register</span></h1>
          <p className="text-slate-500 font-medium text-lg">Inventário de riscos de segurança e planos de tratamento.</p>
        </div>
        <button className="flex items-center gap-2 bg-slate-900 text-white px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-rose-600 transition-all shadow-xl shadow-slate-200">
           <Plus className="w-4 h-4" /> New Risk Entry
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-10">
         <div className="bg-white border border-slate-200 rounded-3xl p-6">
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Total Risks</div>
            <div className="text-3xl font-black text-slate-900">{riskData?.risks?.length || 0}</div>
         </div>
         <div className="bg-rose-50 border border-rose-100 rounded-3xl p-6">
            <div className="text-[10px] font-black uppercase tracking-widest text-rose-400 mb-2">High Severity</div>
            <div className="text-3xl font-black text-rose-600">2</div>
         </div>
         <div className="bg-emerald-50 border border-emerald-100 rounded-3xl p-6">
            <div className="text-[10px] font-black uppercase tracking-widest text-emerald-400 mb-2">Mitigated</div>
            <div className="text-3xl font-black text-emerald-600">75%</div>
         </div>
         <div className="bg-slate-900 rounded-3xl p-6 text-white flex items-center justify-between">
            <div>
               <div className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-2">Residual Score</div>
               <div className="text-3xl font-black">4.2</div>
            </div>
            <BarChart className="w-8 h-8 text-emerald-500" />
         </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
         <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
               <thead>
                  <tr className="bg-slate-50/50 text-[10px] font-black uppercase tracking-widest text-slate-400 border-b border-slate-100">
                     <th className="px-8 py-4">ID</th>
                     <th className="px-8 py-4">Risk Description</th>
                     <th className="px-8 py-4 text-center">Inherent Score</th>
                     <th className="px-8 py-4">Treatment Plan</th>
                     <th className="px-8 py-4">Status</th>
                  </tr>
               </thead>
               <tbody className="divide-y divide-slate-100">
                  {riskData?.risks?.map((risk: any) => (
                    <tr key={risk.id} className="hover:bg-slate-50/50 transition-colors group">
                       <td className="px-8 py-6 font-mono text-xs text-slate-400">{risk.id}</td>
                       <td className="px-8 py-6 max-w-xs">
                          <div className="font-bold text-slate-900 text-sm mb-1">{risk.title}</div>
                          <div className="text-[10px] text-slate-500 font-medium leading-relaxed">{risk.description}</div>
                       </td>
                       <td className="px-8 py-6 text-center">
                          <div className={`inline-flex items-center justify-center w-10 h-10 rounded-xl border text-sm font-black ${getRiskColor(risk.score)}`}>
                             {risk.score}
                          </div>
                       </td>
                       <td className="px-8 py-6">
                          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-[10px] font-medium text-slate-600 leading-relaxed">
                             {risk.treatment_plan}
                          </div>
                       </td>
                       <td className="px-8 py-6">
                          <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${
                             risk.status === 'active' ? 'bg-amber-50 text-amber-600' : 'bg-emerald-50 text-emerald-600'
                          }`}>
                             {risk.status}
                          </span>
                       </td>
                    </tr>
                  ))}
               </tbody>
            </table>
         </div>
      </div>
    </div>
  )
}
