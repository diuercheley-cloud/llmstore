import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import { Shield, ChevronLeft, Search, Filter, Info } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function ControlMap() {
  const { data: controls, isLoading } = useQuery({
    queryKey: ['compliance-control-map'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/control-map')
      return res.data
    }
  })

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10">
        <Link to="/compliance" className="text-muted-foreground hover:text-emerald-600 transition-colors flex items-center gap-1 text-[10px] font-black uppercase tracking-widest mb-4">
           <ChevronLeft className="w-3 h-3" /> Back to Readiness
        </Link>
        <h1 className="text-4xl font-black text-foreground tracking-tight">Control <span className="text-emerald-600">Matrix</span></h1>
        <p className="text-muted-foreground font-medium text-lg">Mapeamento de requisitos técnicos para SOC 2 e ISO 27001.</p>
      </header>

      <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
         <div className="p-6 border-b border-border flex justify-between items-center bg-secondary/50">
            <div className="flex gap-4 items-center">
               <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <input type="text" placeholder="Search controls..." className="pl-10 pr-4 py-2 bg-card border border-border rounded-xl text-xs font-medium focus:outline-none focus:border-emerald-500 w-64" />
               </div>
               <button className="flex items-center gap-2 px-4 py-2 border border-border rounded-xl text-[10px] font-black uppercase tracking-widest text-muted-foreground hover:bg-card transition-all">
                  <Filter className="w-3 h-3" /> Framework
               </button>
            </div>
            <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
               {controls?.length || 0} Controls Mapped
            </div>
         </div>

         <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
               <thead>
                  <tr className="bg-secondary/50 text-[10px] font-black uppercase tracking-widest text-muted-foreground border-b border-border">
                     <th className="px-8 py-4">ID / Code</th>
                     <th className="px-8 py-4">Title</th>
                     <th className="px-8 py-4">Status</th>
                     <th className="px-8 py-4">Owner</th>
                     <th className="px-8 py-4 text-right">Actions</th>
                  </tr>
               </thead>
               <tbody className="divide-y divide-border">
                  {controls?.map((control: any) => (
                    <tr key={control.control_id} className="hover:bg-secondary/50 transition-colors group">
                       <td className="px-8 py-6">
                          <span className="px-3 py-1 bg-foreground text-white text-[10px] font-black rounded-lg uppercase tracking-tighter">
                             {control.control_id}
                          </span>
                       </td>
                       <td className="px-8 py-6">
                          <div className="font-bold text-foreground text-sm mb-1">{control.title}</div>
                          <div className="text-[10px] text-muted-foreground font-medium line-clamp-1">{control.description}</div>
                       </td>
                       <td className="px-8 py-6">
                          <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${
                             control.implementation_status === 'implemented' ? 'bg-emerald-50 text-emerald-600' : 'bg-yellow-500/10 text-yellow-600'
                          }`}>
                             {control.implementation_status}
                          </span>
                       </td>
                       <td className="px-8 py-6">
                          <div className="text-xs font-bold text-muted-foreground">{control.owner_role}</div>
                          <div className="text-[10px] text-muted-foreground uppercase tracking-widest font-black">Review {control.review_frequency}</div>
                       </td>
                       <td className="px-8 py-6 text-right">
                          <button className="p-2 text-muted-foreground hover:text-emerald-600 transition-colors">
                             <Info className="w-4 h-4" />
                          </button>
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
