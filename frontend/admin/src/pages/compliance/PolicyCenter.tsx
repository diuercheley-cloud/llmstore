import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import { BookOpen, ChevronLeft, FileCheck, Clock, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function PolicyCenter() {
  const { data: policies, isLoading } = useQuery({
    queryKey: ['compliance-isms-policies'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/isms/policies')
      return res.data
    }
  })

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10">
        <Link to="/compliance" className="text-muted-foreground hover:text-emerald-600 transition-colors flex items-center gap-1 text-[10px] font-black uppercase tracking-widest mb-4">
           <ChevronLeft className="w-3 h-3" /> Back to Readiness
        </Link>
        <h1 className="text-4xl font-black text-foreground tracking-tight">Policy <span className="text-emerald-600">Center</span></h1>
        <p className="text-muted-foreground font-medium text-lg">Diretrizes formais de segurança e governança.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
         {policies?.map((policy: any, i: number) => (
           <div key={i} className="bg-card border border-border rounded-3xl p-8 hover:border-emerald-300 transition-all group flex flex-col justify-between">
              <div>
                 <div className="flex justify-between items-start mb-6">
                    <div className="p-3 bg-emerald-50 text-emerald-600 rounded-2xl group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                       <BookOpen className="w-6 h-6" />
                    </div>
                    <span className="bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest">
                       Approved
                    </span>
                 </div>
                 <h3 className="text-xl font-black text-foreground mb-4">{policy.name.replace('.md', '').replace(/-/g, ' ').toUpperCase()}</h3>
                 <div className="space-y-3 mb-8">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                       <Clock className="w-3 h-3" /> Review: Annually
                    </div>
                    <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                       <FileCheck className="w-3 h-3" /> Owner: Security Lead
                    </div>
                 </div>
              </div>
              <button className="w-full py-3 rounded-2xl bg-secondary border border-border text-foreground text-[10px] font-black uppercase tracking-widest hover:bg-emerald-50 hover:text-emerald-600 hover:border-emerald-200 transition-all flex items-center justify-center gap-2">
                 Read Policy <ExternalLink className="w-3 h-3" />
              </button>
           </div>
         ))}
      </div>
    </div>
  )
}
