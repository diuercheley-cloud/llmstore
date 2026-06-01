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
          <h1 className="text-4xl font-black text-foreground tracking-tight">Centro de <span className="text-primary">Operações</span></h1>
          <div className="flex items-center gap-3">
             <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Modo:</span>
             <span className="px-3 py-1 bg-foreground text-background text-[10px] font-black rounded-full uppercase">{overview?.deployment_mode || 'Appliance'}</span>
          </div>
        </div>
        <p className="text-muted-foreground font-medium">Monitoramento em tempo real, diagnóstico de prontidão e ações de remediação.</p>
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
              className="flex items-center gap-2 bg-destructive/10 text-destructive hover:bg-destructive/20 px-4 py-2.5 rounded-xl font-bold text-sm transition-colors border border-rose-200"
            >
              <Zap className="w-4 h-4" />
              Resetar Circuit Breaker
            </button>
            <Link 
              to="/operations/readiness"
              className="flex items-center gap-2 bg-secondary text-foreground hover:bg-secondary px-4 py-2.5 rounded-xl font-bold text-sm transition-colors border border-border"
            >
              <CheckCircle2 className="w-4 h-4" />
              Executar Readiness Check
            </Link>
            <button 
              className="flex items-center gap-2 bg-secondary text-foreground hover:bg-secondary px-4 py-2.5 rounded-xl font-bold text-sm transition-colors border border-border"
            >
              <RotateCcw className="w-4 h-4" />
              Forçar Resync de Config
            </button>
          </ActionPanel>

          <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
            <div className="p-6 border-b border-border flex justify-between items-center bg-secondary/50">
              <h3 className="font-black text-foreground uppercase tracking-tight">Recomendações da AIOps</h3>
              <span className="text-[10px] font-bold text-muted-foreground bg-card px-2 py-1 rounded-md border border-border">AUTO-GENERATE</span>
            </div>
            <div className="divide-y divide-border">
              {recommendations?.map((rec: any) => (
                <div key={rec.id} className="p-6 hover:bg-secondary/50 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-bold text-foreground">{rec.title}</h4>
                    <RiskLevelBadge level={rec.priority} />
                  </div>
                  <p className="text-sm text-muted-foreground mb-4">{rec.action}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded uppercase tracking-tighter">{rec.impact}</span>
                    <a href={rec.runbook_url} className="text-xs font-black text-muted-foreground hover:text-primary flex items-center gap-1 uppercase tracking-wider transition-colors">
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
          <div className="bg-foreground text-background rounded-3xl p-8 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <ShieldCheck className="w-24 h-24" />
            </div>
            <h3 className="text-xl font-bold mb-2">Postura de Segurança</h3>
            <p className="text-muted-foreground text-sm mb-6">Sua infraestrutura está seguindo 92% das recomendações de segurança.</p>
            <div className="w-full bg-foreground h-2 rounded-full mb-8">
              <div className="bg-primary h-full rounded-full" style={{ width: '92%' }}></div>
            </div>
            <Link to="/operations/security" className="block text-center bg-card text-foreground font-bold py-3 rounded-2xl hover:bg-primary/10 transition-colors">
              Ver Relatório Completo
            </Link>
          </div>

          <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
            <h3 className="font-black text-foreground uppercase tracking-tight mb-4">Enterprise Features</h3>
            <div className="space-y-3">
              {Object.entries(overview?.enterprise_features || {}).map(([key, enabled]: [string, any]) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">{key.replace(/_/g, ' ')}</span>
                  <span className={`px-2 py-0.5 rounded text-[9px] font-black ${enabled ? 'bg-primary/20 text-primary' : 'bg-secondary text-muted-foreground'}`}>
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
