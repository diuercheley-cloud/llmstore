import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import { ShieldCheck, AlertCircle, BarChart3, BookOpen, ChevronRight, Download, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function ComplianceOverview() {
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['compliance-status'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/isms/status')
      return res.data
    }
  })

  const { data: controlMap } = useQuery({
    queryKey: ['compliance-control-map-overview'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/control-map')
      return res.data
    }
  })

  const { data: riskData } = useQuery({
    queryKey: ['compliance-risk-register-overview'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/isms/risk-register')
      return res.data
    }
  })

  const { data: evidenceIndex } = useQuery({
    queryKey: ['compliance-evidence-overview'],
    queryFn: async () => {
      const res = await api.get('/admin/compliance/evidence/latest')
      return res.data
    }
  })

  if (statusLoading) return <div className="p-8 font-black uppercase text-muted-foreground">Analisando Prontidão...</div>

  const controls = controlMap || []
  const risks = riskData?.risks || []
  const evidenceItems = evidenceIndex || []
  const readiness = Number(status?.soa_progress ?? 0)
  const activeControls = controls.filter((item: any) => item.implementation_status === 'implemented').length
  const partialControls = controls.filter((item: any) => item.implementation_status === 'partial').length

  const getControlStatusLabel = (value: string) => {
    if (value === 'implemented') return 'Implementado'
    if (value === 'partial') return 'Parcial'
    return 'Pendente'
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Prontidão de <span className="text-emerald-600">conformidade</span></h1>
          <p className="max-w-3xl text-muted-foreground font-medium text-lg">Visão executiva de conformidade SOC 2 e ISO 27001. {status?.framework ? `Estrutura: ${status.framework}.` : ''}</p>
        </div>
        <div className="flex gap-4">
          <Link to="/compliance/evidence" className="flex items-center gap-2 bg-foreground text-background px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-emerald-600 transition-all shadow-xl shadow-slate-200">
            <RefreshCw className="w-4 h-4" />
            Sincronizar evidências
          </Link>
          <Link to="/compliance/controls" className="flex items-center gap-2 bg-emerald-600 text-white px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-emerald-700 transition-all shadow-xl shadow-emerald-200">
            <Download className="w-4 h-4" />
            Exportar pacote
          </Link>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mb-10">
        <div className="bg-card border border-border rounded-3xl p-8 min-h-[180px] flex flex-col justify-between transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
          <div className="text-muted-foreground text-[10px] font-black uppercase tracking-widest mb-4">Prontidão geral</div>
          <div className="text-5xl font-black text-foreground mb-6">{Math.round(readiness)}%</div>
          <div className="h-2 bg-secondary rounded-full overflow-hidden">
            <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.min(100, readiness)}%` }}></div>
          </div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-8 min-h-[180px] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
          <div className="text-muted-foreground text-[10px] font-black uppercase tracking-widest mb-4">Riscos ativos</div>
          <div className="text-5xl font-black text-foreground">{risks.length}</div>
          <div className="text-[10px] font-bold text-yellow-600 mt-2">{risks.length > 0 ? 'Requer mitigação' : 'Não há riscos abertos'}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-8 min-h-[180px] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
          <div className="text-muted-foreground text-[10px] font-black uppercase tracking-widest mb-4">Controles implementados</div>
          <div className="text-5xl font-black text-foreground">{activeControls}</div>
          <div className="text-[10px] font-bold text-emerald-600 mt-2">Operacionais</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-8 min-h-[180px] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
          <div className="text-muted-foreground text-[10px] font-black uppercase tracking-widest mb-4">Controles parciais</div>
          <div className="text-5xl font-black text-foreground">{partialControls}</div>
          <div className="text-[10px] font-bold text-yellow-600 mt-2">Precisam de evidência</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-8 min-h-[180px] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
          <div className="text-muted-foreground text-[10px] font-black uppercase tracking-widest mb-4">Políticas ativas</div>
          <div className="text-5xl font-black text-foreground">{status?.policies_count || 0}</div>
          <div className="text-[10px] font-bold text-indigo-600 mt-2">Carregadas do backend</div>
        </div>
        <div className="bg-cyan-950 rounded-3xl p-8 min-h-[180px] text-white transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl">
          <div className="text-muted-foreground text-[10px] font-black uppercase tracking-widest mb-4">Evidências coletadas</div>
          <div className="text-5xl font-black">{evidenceItems.length}</div>
          <div className="text-[10px] font-bold text-cyan-300 mt-2">Índice mais recente do backend</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card border border-border rounded-3xl p-8 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <div className="flex justify-between items-center mb-8">
              <h2 className="text-xl font-black uppercase tracking-tight">Módulos de conformidade</h2>
              <Link to="/compliance/controls" className="text-emerald-600 text-[10px] font-black uppercase tracking-widest hover:underline">Acessar controles</Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {controls.slice(0, 4).map((item: any) => (
                <div key={`${item.framework}-${item.control_id}`} className="p-4 border border-border rounded-2xl hover:border-emerald-200 transition-colors flex items-center gap-4">
                  <div className={`p-3 rounded-xl ${item.implementation_status === 'implemented' ? 'bg-emerald-50 text-emerald-600' : item.implementation_status === 'partial' ? 'bg-yellow-500/10 text-yellow-600' : 'bg-secondary text-muted-foreground'}`}>
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-black uppercase tracking-tight text-foreground truncate">{item.title}</div>
                    <div className="text-[10px] font-bold uppercase text-muted-foreground">{item.framework} • {item.control_id}</div>
                    <div className={`text-[10px] font-bold uppercase mt-1 ${item.implementation_status === 'implemented' ? 'text-emerald-500' : item.implementation_status === 'partial' ? 'text-yellow-500' : 'text-muted-foreground'}`}>{getControlStatusLabel(item.implementation_status)}</div>
                  </div>
                </div>
              ))}
              {controls.length === 0 && (
                <div className="p-4 border border-dashed border-border rounded-2xl text-sm text-muted-foreground">
                  Não há controles mapeados.
                </div>
              )}
            </div>
          </div>

          <div className="bg-card border border-border rounded-3xl p-8 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <div className="flex items-center gap-2 mb-8">
              <div className="w-2.5 h-2.5 rounded-full bg-cyan-500"></div>
              <h2 className="text-xl font-black uppercase tracking-tight">Evidências recentes</h2>
            </div>
            <div className="space-y-4">
              {evidenceItems.slice(0, 3).map((item: any) => (
                <div key={item.hash_sha256} className="flex justify-between items-center p-4 bg-secondary rounded-2xl border border-border hover:bg-cyan-50 hover:border-cyan-200 hover:shadow-lg transition-all group">
                  <div>
                    <div className="text-xs font-black text-foreground uppercase tracking-tight">{item.source}</div>
                    <div className="text-[10px] text-muted-foreground font-medium">{item.original_path}</div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-[8px] font-mono text-muted-foreground hidden group-hover:block">{item.hash_sha256.substring(0, 16)}...</span>
                    <ChevronRight className="w-4 h-4 text-cyan-500" />
                  </div>
                </div>
              ))}
              {evidenceItems.length === 0 && (
                <div className="p-8 text-center text-muted-foreground">
                  Não há evidências recentes.
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-yellow-500/10 border border-amber-100 rounded-3xl p-8 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <div className="flex items-center gap-2 mb-4 text-amber-900">
              <AlertCircle className="w-5 h-5" />
              <h3 className="font-black uppercase tracking-tight text-sm">Gaps críticos</h3>
            </div>
            <div className="space-y-4">
              {risks.slice(0, 2).map((risk: any) => (
                <div key={risk.id} className="p-4 bg-card/50 rounded-2xl">
                  <div className="text-[10px] font-black uppercase text-yellow-600 mb-1">{risk.id || 'RISK'}</div>
                  <p className="text-xs text-amber-900 font-medium leading-relaxed">{risk.title}</p>
                  <p className="text-[10px] text-amber-900/70 font-medium leading-relaxed mt-2">{risk.treatment_plan}</p>
                </div>
              ))}
              {risks.length === 0 && (
                <div className="p-4 bg-card/50 rounded-2xl">
                  <div className="text-[10px] font-black uppercase text-yellow-600 mb-1">Não há riscos abertos</div>
                  <p className="text-xs text-amber-900 font-medium leading-relaxed">O registro está vazio no momento.</p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-secondary border border-border rounded-3xl p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
            <h4 className="text-[10px] font-black uppercase text-muted-foreground mb-4 tracking-widest">Atalhos</h4>
            <div className="space-y-2">
              <Link to="/compliance/risks" className="flex items-center justify-between p-3 rounded-xl hover:bg-card transition-all text-xs font-bold text-muted-foreground">Acessar riscos <ChevronRight className="w-3 h-3" /></Link>
              <Link to="/compliance/policies" className="flex items-center justify-between p-3 rounded-xl hover:bg-card transition-all text-xs font-bold text-muted-foreground">Acessar políticas <ChevronRight className="w-3 h-3" /></Link>
              <Link to="/compliance/evidence" className="flex items-center justify-between p-3 rounded-xl hover:bg-card transition-all text-xs font-bold text-muted-foreground">Acessar evidências <ChevronRight className="w-3 h-3" /></Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
