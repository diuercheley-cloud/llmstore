import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import { ShieldCheck, FileCheck, AlertCircle, BarChart3, BookOpen, Clock, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function ComplianceDashboard() {
  const { data: frameworks, isLoading } = useQuery({
    queryKey: ['compliance-frameworks'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/frameworks')
      return res.data
    }
  })

  const { data: status } = useQuery({
    queryKey: ['compliance-status-dashboard'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/isms/status')
      return res.data
    }
  })

  const { data: controlMap } = useQuery({
    queryKey: ['compliance-control-map-dashboard'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/control-map')
      return res.data
    }
  })

  const { data: riskData } = useQuery({
    queryKey: ['compliance-risk-register-dashboard'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/isms/risk-register')
      return res.data
    }
  })

  const { data: evidenceIndex } = useQuery({
    queryKey: ['compliance-evidence-dashboard'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/evidence/latest')
      return res.data
    }
  })

  if (isLoading) return <div className="p-8 font-black uppercase text-muted-foreground">Analisando Prontidão...</div>

  const controls = controlMap || []
  const risks = riskData?.risks || []
  const evidenceItems = evidenceIndex || []
  const implementedCount = controls.filter((control: any) => control.implementation_status === 'implemented').length
  const partialCount = controls.filter((control: any) => control.implementation_status === 'partial').length
  const readiness = Number(status?.soa_progress ?? 0)

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Prontidão de <span className="text-emerald-600">conformidade</span></h1>
          <p className="max-w-3xl text-muted-foreground font-medium text-lg">Preparação para auditorias SOC 2 e ISO 27001. {status?.framework ? `Estrutura ativa: ${status.framework}.` : ''}</p>
        </div>
        <div className="flex gap-4">
           <div className="flex items-center gap-2 bg-emerald-50 text-emerald-700 px-4 py-2 rounded-2xl border border-emerald-100">
             <ShieldCheck className="w-4 h-4" />
             <span className="text-xs font-black uppercase tracking-widest">Pronto para auditoria: {Math.round(readiness)}%</span>
           </div>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {frameworks?.map((fw: any) => {
              const fwControls = controls.filter((control: any) => control.framework === fw.name)
              const fwImplemented = fwControls.filter((control: any) => control.implementation_status === 'implemented').length
              const fwReadiness = fwControls.length > 0 ? Math.round((fwImplemented / fwControls.length) * 100) : 0
              return (
              <div key={fw.id} className="bg-card border border-border rounded-3xl p-8 min-h-[320px] hover:border-emerald-300 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg group">
                <div className="flex justify-between items-start mb-6">
                  <div className="p-3 bg-emerald-50 text-emerald-600 rounded-2xl group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                    <FileCheck className="w-6 h-6" />
                  </div>
                  <span className="bg-secondary text-muted-foreground px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-tighter">
                    v{fw.version}
                  </span>
                </div>
                <h3 className="text-2xl font-black text-foreground mb-2">{fw.name}</h3>
                <p className="text-sm text-muted-foreground mb-8 font-medium leading-relaxed">{fw.description}</p>
                
                <div className="space-y-4">
                   <div className="h-2 bg-secondary rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.min(100, fwReadiness)}%` }}></div>
                   </div>
                   <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                      <span>Prontidão</span>
                      <span className="text-emerald-600">{fwReadiness}% concluído</span>
                   </div>
                </div>

                <Link to="/compliance/controls" className="w-full mt-8 py-3 rounded-2xl bg-foreground text-background text-[10px] font-black uppercase tracking-widest hover:bg-emerald-600 transition-colors flex items-center justify-center gap-2">
                   Acessar controles <ChevronRight className="w-3 h-3" />
                </Link>
              </div>
            )})}
          </div>

          <div className="bg-foreground text-background rounded-3xl p-8 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl">
             <div className="flex items-center gap-3 mb-6">
                <BarChart3 className="w-6 h-6 text-emerald-400" />
                <h2 className="text-xl font-black uppercase tracking-tight">Resumo executivo</h2>
             </div>
             <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                <div className="p-6 rounded-2xl bg-foreground/50 border border-border">
                   <div className="text-muted-foreground text-[10px] font-black uppercase tracking-widest mb-2">Controles totais</div>
                   <div className="text-3xl font-black">{controls.length}</div>
                </div>
                <div className="p-6 rounded-2xl bg-foreground/50 border border-border">
                   <div className="text-emerald-400 text-[10px] font-black uppercase tracking-widest mb-2">Implementado</div>
                   <div className="text-3xl font-black text-emerald-400">{implementedCount}</div>
                </div>
                <div className="p-6 rounded-2xl bg-foreground/50 border border-border">
                   <div className="text-amber-400 text-[10px] font-black uppercase tracking-widest mb-2">Pendente</div>
                   <div className="text-3xl font-black text-amber-400">{partialCount + Math.max(0, controls.length - implementedCount - partialCount)}</div>
                </div>
             </div>
          </div>
        </div>

        <div className="space-y-6">
           <div className="bg-card border border-border rounded-3xl p-6 min-h-[260px] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
              <div className="flex items-center gap-2 mb-6 text-foreground">
                <Clock className="w-5 h-5 text-cyan-600" />
                <h3 className="font-black uppercase tracking-tight text-sm">Evidências recentes</h3>
              </div>
              <div className="space-y-4">
                 {evidenceItems.slice(0, 3).map((item: any) => (
                   <div key={item.hash_sha256} className="flex justify-between items-center p-3 rounded-xl hover:bg-cyan-50 transition-colors">
                      <div>
                         <div className="font-bold text-xs">{item.source}</div>
                         <div className="text-[10px] text-muted-foreground">{new Date(item.collected_at).toLocaleString()}</div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-cyan-500" />
                   </div>
                 ))}
                 {evidenceItems.length === 0 && (
                   <div className="text-sm text-muted-foreground">Nenhuma evidência recente encontrada.</div>
                 )}
              </div>
           </div>

           <div className="bg-indigo-950 text-white rounded-3xl p-8 min-h-[260px] relative overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl">
              <BookOpen className="w-24 h-24 absolute -bottom-6 -right-6 text-indigo-900/50" />
              <h3 className="text-lg font-black mb-2 relative z-10">Políticas de segurança</h3>
              <p className="text-sm text-indigo-100/70 mb-6 font-medium relative z-10 leading-relaxed">
                Acesse o repositório central de políticas aprovadas para ISO 27001.
              </p>
              <Link to="/compliance/policies" className="inline-flex bg-card text-indigo-900 px-6 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest hover:bg-indigo-50 transition-colors relative z-10">
                Acessar políticas
              </Link>
           </div>

           <div className="p-6 bg-secondary rounded-3xl border border-border min-h-[180px] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
              <div className="flex items-start gap-3">
                 <AlertCircle className="w-5 h-5 text-muted-foreground mt-0.5" />
                 <div>
                    <h4 className="text-xs font-black uppercase text-foreground mb-1">Nota legal</h4>
                    <p className="text-[10px] text-muted-foreground font-medium leading-relaxed">
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
