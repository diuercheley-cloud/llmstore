import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import { ShieldCheck, FileCheck, AlertCircle, BarChart3, BookOpen, Clock, ChevronRight, Download, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function ComplianceOverview() {
  const { data: status, isLoading } = useQuery({
    queryKey: ['compliance-status'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/isms/status')
      return res.data
    }
  })

  if (isLoading) return <div className="p-8 font-black uppercase text-slate-400">Analisando Prontidão...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Compliance <span className="text-emerald-600">Readiness</span></h1>
          <p className="text-slate-500 font-medium text-lg">Visão executiva de conformidade SOC 2 e ISO 27001.</p>
        </div>
        <div className="flex gap-4">
           <button className="flex items-center gap-2 bg-slate-900 text-white px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-emerald-600 transition-all shadow-xl shadow-slate-200">
             <RefreshCw className="w-4 h-4" />
             Collect Evidence
           </button>
           <button className="flex items-center gap-2 bg-emerald-600 text-white px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-emerald-700 transition-all shadow-xl shadow-emerald-200">
             <Download className="w-4 h-4" />
             Audit Package
           </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-10">
         <div className="bg-white border border-slate-200 rounded-3xl p-8 flex flex-col justify-between">
            <div className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-4">Overall Readiness</div>
            <div className="text-5xl font-black text-slate-900 mb-6">{Math.round(status?.soa_progress || 0)}%</div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
               <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${status?.soa_progress || 0}%` }}></div>
            </div>
         </div>
         <div className="bg-white border border-slate-200 rounded-3xl p-8">
            <div className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-4">Active Risks</div>
            <div className="text-5xl font-black text-slate-900">{status?.risks_count || 0}</div>
            <div className="text-[10px] font-bold text-amber-600 mt-2">Requires Mitigation</div>
         </div>
         <div className="bg-white border border-slate-200 rounded-3xl p-8">
            <div className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-4">Active Policies</div>
            <div className="text-5xl font-black text-slate-900">{status?.policies_count || 0}</div>
            <div className="text-[10px] font-bold text-emerald-600 mt-2">All Approved</div>
         </div>
         <div className="bg-slate-900 rounded-3xl p-8 text-white">
            <div className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-4">Internal Audits</div>
            <div className="text-5xl font-black">2</div>
            <div className="text-[10px] font-bold text-emerald-400 mt-2">Last: 15 days ago</div>
         </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
         <div className="lg:col-span-2 space-y-6">
            <div className="bg-white border border-slate-200 rounded-3xl p-8">
               <div className="flex justify-between items-center mb-8">
                  <h2 className="text-xl font-black uppercase tracking-tight">Compliance Modules</h2>
                  <Link to="/compliance/controls" className="text-emerald-600 text-[10px] font-black uppercase tracking-widest hover:underline">View All Controls</Link>
               </div>
               <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[
                    { t: 'Access Control', s: 'implemented', i: ShieldCheck },
                    { t: 'Operations Security', s: 'partial', i: Activity },
                    { t: 'Change Management', s: 'implemented', i: RefreshCw },
                    { t: 'Incident Response', s: 'partial', i: AlertCircle },
                  ].map((item, i) => (
                    <div key={i} className="p-4 border border-slate-100 rounded-2xl hover:border-emerald-200 transition-colors flex items-center gap-4">
                       <div className={`p-3 rounded-xl ${item.s === 'implemented' ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'}`}>
                          <item.i className="w-5 h-5" />
                       </div>
                       <div className="flex-1">
                          <div className="text-xs font-black uppercase tracking-tight text-slate-900">{item.t}</div>
                          <div className={`text-[10px] font-bold uppercase ${item.s === 'implemented' ? 'text-emerald-500' : 'text-amber-500'}`}>{item.s}</div>
                       </div>
                    </div>
                  ))}
               </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-3xl p-8">
               <h2 className="text-xl font-black uppercase tracking-tight mb-8">Recent Evidence Items</h2>
               <div className="space-y-4">
                  {[
                    { t: 'SOC 2 Access Review - Q2 2026', d: 'Collected 2 hours ago', h: 'SHA256: 4a2b1c...' },
                    { t: 'Release Gate Validation - v1.9.6', d: 'Collected 1 day ago', h: 'SHA256: 9f8e7d...' },
                    { t: 'Chaos Resilience Report', d: 'Collected 2 days ago', h: 'SHA256: 3c4d5e...' }
                  ].map((item, i) => (
                    <div key={i} className="flex justify-between items-center p-4 bg-slate-50 rounded-2xl border border-slate-100 hover:bg-white hover:shadow-lg transition-all group">
                       <div>
                          <div className="text-xs font-black text-slate-900 uppercase tracking-tight">{item.t}</div>
                          <div className="text-[10px] text-slate-400 font-medium">{item.d}</div>
                       </div>
                       <div className="flex items-center gap-4">
                          <span className="text-[8px] font-mono text-slate-300 hidden group-hover:block">{item.h}</span>
                          <ChevronRight className="w-4 h-4 text-slate-300" />
                       </div>
                    </div>
                  ))}
               </div>
            </div>
         </div>

         <div className="space-y-6">
            <div className="bg-amber-50 border border-amber-100 rounded-3xl p-8">
               <div className="flex items-center gap-2 mb-4 text-amber-900">
                  <AlertCircle className="w-5 h-5" />
                  <h3 className="font-black uppercase tracking-tight text-sm">Critical Gaps</h3>
               </div>
               <div className="space-y-4">
                  <div className="p-4 bg-white/50 rounded-2xl">
                     <div className="text-[10px] font-black uppercase text-amber-700 mb-1">SOC 2 CC7.2</div>
                     <p className="text-xs text-amber-900 font-medium leading-relaxed">Anomaly detection is currently in advisory mode. Real-time blocking required.</p>
                  </div>
                  <div className="p-4 bg-white/50 rounded-2xl">
                     <div className="text-[10px] font-black uppercase text-amber-700 mb-1">ISO A.14.2.1</div>
                     <p className="text-xs text-amber-900 font-medium leading-relaxed">Secure development training for operators not yet documented.</p>
                  </div>
               </div>
            </div>

            <div className="bg-slate-50 border border-slate-100 rounded-3xl p-6">
               <h4 className="text-[10px] font-black uppercase text-slate-400 mb-4 tracking-widest">Compliance Links</h4>
               <div className="space-y-2">
                  <Link to="/compliance/risks" className="flex items-center justify-between p-3 rounded-xl hover:bg-white transition-all text-xs font-bold text-slate-600">Risk Register <ChevronRight className="w-3 h-3" /></Link>
                  <Link to="/compliance/policies" className="flex items-center justify-between p-3 rounded-xl hover:bg-white transition-all text-xs font-bold text-slate-600">Policy Center <ChevronRight className="w-3 h-3" /></Link>
                  <Link to="/compliance/evidence" className="flex items-center justify-between p-3 rounded-xl hover:bg-white transition-all text-xs font-bold text-slate-600">Evidence Center <ChevronRight className="w-3 h-3" /></Link>
               </div>
            </div>
         </div>
      </div>
    </div>
  )
}
