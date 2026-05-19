import { useQuery, useMutation } from '@tanstack/react-query'
import api from '../../lib/api'
import HealthCard from '../../components/operations/HealthCard'
import ActionPanel from '../../components/operations/ActionPanel'
import { Activity, Cpu, Box, AlertTriangle, ShieldCheck, Zap, RotateCcw, FileText, CheckCircle2 } from 'lucide-react'
import StatusBadge from '../../components/operations/StatusBadge'
import RiskLevelBadge from '../../components/operations/RiskLevelBadge'
import { Link } from 'react-router-dom'
import { useState } from 'react'
import ConfirmDangerActionModal from '../../components/operations/ConfirmDangerActionModal'

export default function OperationsOverview() {
  const [isResetCBModalOpen, setIsResetCBModalOpen] = useState(false)

  const { data: overview, isLoading } = useQuery({
    queryKey: ['ops-overview'],
    queryFn: async () => {
      const res = await api.get('/admin/operations/overview')
      return res.data
    },
    refetchInterval: 10000
  })

  const { data: recommendations } = useQuery({
    queryKey: ['ops-recommendations'],
    queryFn: async () => {
      const res = await api.get('/admin/operations/recommendations')
      return res.data
    }
  })

  const resetCBMutation = useMutation({
    mutationFn: async () => {
      return api.post('/admin/operations/reset-circuit-breaker')
    },
    onSuccess: () => {
      setIsResetCBModalOpen(false)
    }
  })

  if (isLoading) return <div className="p-8 text-center">Carregando overview operacional...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Centro de <span className="text-teal-600">Operações</span></h1>
          <div className="flex items-center gap-3">
             <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Modo:</span>
             <span className="px-3 py-1 bg-slate-900 text-white text-[10px] font-black rounded-full uppercase">{overview?.deployment_mode || 'Appliance'}</span>
          </div>
        </div>
        <p className="text-slate-500 font-medium">Monitoramento em tempo real, diagnóstico de prontidão e ações de remediação.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <HealthCard 
          title="Status Global" 
          value={overview?.status === 'healthy' ? 'Operacional' : 'Instável'} 
          status={overview?.status === 'healthy' ? 'healthy' : 'warning'}
          icon={<Activity className="w-6 h-6" />}
          description="Todos os sistemas principais respondendo."
        />
        <HealthCard 
          title="Nós de Runtime" 
          value={`${overview?.healthy_nodes}/${overview?.active_nodes}`} 
          status={overview?.healthy_nodes === overview?.active_nodes ? 'healthy' : 'warning'}
          icon={<Cpu className="w-6 h-6" />}
          description="Nós ativos processando inferência."
        />
        <HealthCard 
          title="Modelos Ativos" 
          value={overview?.active_models || 0} 
          icon={<Box className="w-6 h-6" />}
          description="Modelos carregados e prontos para uso."
        />
        <HealthCard 
          title="Risco Estimado" 
          value={overview?.risk_level?.toUpperCase() || 'LOW'} 
          status={overview?.risk_level === 'low' ? 'healthy' : 'warning'}
          icon={<ShieldCheck className="w-6 h-6" />}
          description="Probabilidade de falha nas próximas 24h."
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
        <div className="lg:col-span-2 space-y-6">
          <ActionPanel 
            title="Ações Rápidas de Emergência" 
            description="Intervenções críticas para estabilização do sistema."
          >
            <button 
              onClick={() => setIsResetCBModalOpen(true)}
              className="flex items-center gap-2 bg-rose-50 text-rose-700 hover:bg-rose-100 px-4 py-2.5 rounded-xl font-bold text-sm transition-colors border border-rose-200"
            >
              <Zap className="w-4 h-4" />
              Resetar Circuit Breaker
            </button>
            <Link 
              to="/operations/readiness"
              className="flex items-center gap-2 bg-slate-50 text-slate-700 hover:bg-slate-100 px-4 py-2.5 rounded-xl font-bold text-sm transition-colors border border-slate-200"
            >
              <CheckCircle2 className="w-4 h-4" />
              Executar Readiness Check
            </Link>
            <button 
              className="flex items-center gap-2 bg-slate-50 text-slate-700 hover:bg-slate-100 px-4 py-2.5 rounded-xl font-bold text-sm transition-colors border border-slate-200"
            >
              <RotateCcw className="w-4 h-4" />
              Forçar Resync de Config
            </button>
          </ActionPanel>

          <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h3 className="font-black text-slate-900 uppercase tracking-tight">Recomendações da AIOps</h3>
              <span className="text-[10px] font-bold text-slate-400 bg-white px-2 py-1 rounded-md border border-slate-200">AUTO-GENERATE</span>
            </div>
            <div className="divide-y divide-slate-100">
              {recommendations?.map((rec: any) => (
                <div key={rec.id} className="p-6 hover:bg-slate-50/50 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-bold text-slate-900">{rec.title}</h4>
                    <RiskLevelBadge level={rec.priority} />
                  </div>
                  <p className="text-sm text-slate-500 mb-4">{rec.action}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-teal-600 bg-teal-50 px-2 py-0.5 rounded uppercase tracking-tighter">{rec.impact}</span>
                    <a href={rec.runbook_url} className="text-xs font-black text-slate-400 hover:text-teal-600 flex items-center gap-1 uppercase tracking-wider transition-colors">
                      <FileText className="w-3.5 h-3.5" />
                      View Runbook
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-slate-900 text-white rounded-3xl p-8 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <ShieldCheck className="w-24 h-24" />
            </div>
            <h3 className="text-xl font-bold mb-2">Postura de Segurança</h3>
            <p className="text-slate-400 text-sm mb-6">Sua infraestrutura está seguindo 92% das recomendações de segurança.</p>
            <div className="w-full bg-slate-800 h-2 rounded-full mb-8">
              <div className="bg-teal-500 h-full rounded-full" style={{ width: '92%' }}></div>
            </div>
            <Link to="/operations/security" className="block text-center bg-white text-slate-900 font-bold py-3 rounded-2xl hover:bg-teal-50 transition-colors">
              Ver Relatório Completo
            </Link>
          </div>

          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
            <h3 className="font-black text-slate-900 uppercase tracking-tight mb-4">Enterprise Features</h3>
            <div className="space-y-3">
              {Object.entries(overview?.enterprise_features || {}).map(([key, enabled]: [string, any]) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">{key.replace(/_/g, ' ')}</span>
                  <span className={`px-2 py-0.5 rounded text-[9px] font-black ${enabled ? 'bg-teal-100 text-teal-700' : 'bg-slate-100 text-slate-400'}`}>
                    {enabled ? 'OPT-IN' : 'OPT-OFF'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <ConfirmDangerActionModal 
        isOpen={isResetCBModalOpen}
        onClose={() => setIsResetCBModalOpen(false)}
        onConfirm={() => resetCBMutation.mutate()}
        title="Resetar Circuit Breaker"
        description="Esta ação irá resetar todos os contadores de falha e abrir novamente todos os circuitos fechados. Isso pode causar picos de erro se a causa raiz ainda não foi resolvida."
        confirmLabel="Resetar Agora"
        isPending={resetCBMutation.isPending}
      />
    </div>
  )
}
