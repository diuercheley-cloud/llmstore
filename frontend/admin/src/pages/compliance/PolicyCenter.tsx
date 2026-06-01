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

  const policyList = policies || []

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10">
          <Link to="/compliance" className="text-muted-foreground hover:text-indigo-600 transition-colors flex items-center gap-1 text-[10px] font-black uppercase tracking-widest mb-4">
           <ChevronLeft className="w-3 h-3" /> Voltar ao resumo
          </Link>
        <h1 className="text-4xl font-black text-foreground tracking-tight">Central de <span className="text-indigo-600">políticas</span></h1>
        <p className="text-muted-foreground font-medium text-lg">Diretrizes formais de segurança e governança.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
         {policyList.map((policy: any, i: number) => (
           <div key={i} className="bg-card border border-border rounded-3xl p-8 min-h-[280px] hover:border-indigo-300 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg group flex flex-col justify-between">
              <div>
                 <div className="flex justify-between items-start mb-6">
                    <div className="p-3 bg-indigo-50 text-indigo-600 rounded-2xl group-hover:bg-indigo-600 group-hover:text-white transition-colors duration-150">
                       <BookOpen className="w-6 h-6" />
                    </div>
                    <span className="bg-indigo-50 text-indigo-600 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest">
                       Documento
                    </span>
                 </div>
                 <h3 className="text-xl font-black text-foreground mb-4">{policy.name.replace('.md', '').replace(/-/g, ' ').toUpperCase()}</h3>
                 <div className="space-y-3 mb-8">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                       <Clock className="w-3 h-3" /> Caminho: {policy.path}
                    </div>
                    <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                       <FileCheck className="w-3 h-3" /> Arquivo: {policy.name}
                    </div>
                 </div>
              </div>
              <button className="mt-auto w-full py-3 rounded-2xl bg-secondary border border-border text-foreground text-[10px] font-black uppercase tracking-widest hover:bg-indigo-50 hover:text-indigo-600 hover:border-indigo-200 transition-all duration-200 flex items-center justify-center gap-2">
                 Abrir política <ExternalLink className="w-3 h-3" />
              </button>
           </div>
         ))}
         {policyList.length === 0 && (
           <div className="col-span-full p-8 bg-card border border-border rounded-3xl text-muted-foreground">
             Nenhuma política encontrada.
           </div>
         )}
      </div>
    </div>
  )
}
