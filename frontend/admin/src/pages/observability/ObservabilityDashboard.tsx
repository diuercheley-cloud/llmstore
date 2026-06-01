import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import HealthCard from '../../components/operations/HealthCard'
import { Activity, ShieldAlert, BarChart3, Clock, ExternalLink, AlertTriangle, Zap } from 'lucide-react'

export default function ObservabilityDashboard() {
  const { data: dashboardLinks } = useQuery({
    queryKey: ['dashboard-links'],
    queryFn: async () => {
      const res = await api.get('/admin/observability/dashboard-links')
      return res.data
    }
  })

  const { data: errorBudget } = useQuery({
    queryKey: ['error-budget'],
    queryFn: async () => {
      const res = await api.get('/admin/observability/error-budget')
      return res.data
    }
  })

  const { data: platformHealth } = useQuery({
    queryKey: ['platform-health'],
    queryFn: async () => {
      const res = await api.get('/admin/observability/platform-health')
      return res.data
    }
  })

  const { data: sloReport } = useQuery({
    queryKey: ['slo-report'],
    queryFn: async () => {
      const res = await api.get('/admin/observability/slo')
      return res.data
    }
  })

  const { data: metrics } = useQuery({
    queryKey: ['derived-metrics'],
    queryFn: async () => {
      const res = await api.get('/admin/observability/metrics/derived')
      return res.data
    }
  })

  const { data: incidentTimeline } = useQuery({
    queryKey: ['incident-timeline'],
    queryFn: async () => {
      const res = await api.get('/admin/observability/timeline')
      return res.data
    }
  })

  const incidents = incidentTimeline?.items || []
  const availability = Number(errorBudget?.current_availability ?? 99.9)
  const remainingBudget = Number(errorBudget?.remaining_budget_percent ?? 85)
  const burnRate = Number(errorBudget?.burn_rate ?? 1.0)
  const reliabilityScore = Number(metrics?.provider_reliability_score ?? 0)
  const platformStatus = platformHealth?.status || 'unknown'

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10">
        <h1 className="text-4xl font-black text-foreground tracking-tight">Advanced <span className="text-primary">Observability</span></h1>
        <p className="text-muted-foreground font-medium text-lg max-w-3xl">Visibilidade profunda sobre saúde, performance e compliance. A página usa os endpoints de observabilidade reais e mostra fallback quando não há dados.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <HealthCard 
          title="Availability (30d)" 
          value={`${availability.toFixed(2)}%`} 
          status="healthy"
          icon={<Activity className="w-6 h-6" />}
          description="Target: 99.9%"
        />
        <HealthCard 
          title="Error Budget" 
          value={`${remainingBudget.toFixed(1)}%`} 
          status={remainingBudget < 20 ? 'warning' : 'healthy'}
          icon={<BarChart3 className="w-6 h-6" />}
          description="Orçamento de erro restante."
        />
        <HealthCard 
          title="Burn Rate" 
          value={`${burnRate.toFixed(1)}x`} 
          status={burnRate > 2 ? 'warning' : 'healthy'}
          icon={<Clock className="w-6 h-6" />}
          description="Velocidade de consumo do budget."
        />
        <HealthCard 
          title="Reliability Score" 
          value={`${(reliabilityScore * 100).toFixed(1)}%`} 
          icon={<Zap className="w-6 h-6" />}
          description="Score agregado de providers."
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
            <div className="p-6 border-b border-border flex justify-between items-center bg-secondary/50">
              <h3 className="font-black text-foreground uppercase tracking-tight">Timeline de Incidentes</h3>
              <ShieldAlert className="w-5 h-5 text-destructive" />
            </div>
            <div className="divide-y divide-border">
              {incidents.map((incident: any) => (
                <div key={incident.id} className="p-6 hover:bg-secondary/50 transition-colors flex gap-4">
                  <div className={`mt-1 p-2 rounded-xl ${
                    incident.severity === 'high' ? 'bg-destructive/10 text-destructive' : 
                    incident.severity === 'medium' ? 'bg-yellow-500/10 text-yellow-600' : 'bg-accent/10 text-accent'
                  }`}>
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h4 className="font-bold text-foreground">{incident.title}</h4>
                      <span className="text-[10px] font-mono text-muted-foreground">{new Date(incident.timestamp).toLocaleString()}</span>
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed">{incident.description}</p>
                    <div className="mt-3 flex gap-2">
                       <span className="bg-secondary text-muted-foreground text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-tighter">
                         {incident.type}
                       </span>
                    </div>
                  </div>
                </div>
              ))}
              {incidents.length === 0 && (
                <div className="p-8 text-center text-muted-foreground">
                  Nenhum incidente encontrado no período atual.
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
              <h3 className="font-black text-foreground uppercase tracking-tight mb-4">SLO Status</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs font-bold mb-1.5">
                    <span className="text-muted-foreground uppercase">Availability Target</span>
                    <span className="text-foreground">{sloReport?.api_availability?.target ? `${(sloReport.api_availability.target * 100).toFixed(1)}%` : '99.9%'}</span>
                  </div>
                  <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
                    <div className="bg-primary h-full" style={{ width: `${Math.min(100, (availability / 100) * 100)}%` }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs font-bold mb-1.5">
                    <span className="text-muted-foreground uppercase">Latency p95 Target</span>
                    <span className="text-foreground">{sloReport?.p95_latency?.target ? `${sloReport.p95_latency.target.toFixed(1)}s` : '2.0s'}</span>
                  </div>
                  <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
                    <div className="bg-yellow-500/100 h-full w-[85%]"></div>
                  </div>
                </div>
                <div className="pt-2 border-t border-border">
                  <div className="flex items-center justify-between text-xs font-bold">
                    <span className="text-muted-foreground uppercase">Platform Health</span>
                    <span className={platformStatus === 'ok' ? 'text-emerald-600' : platformStatus === 'warning' ? 'text-yellow-600' : 'text-destructive'}>
                      {platformStatus}
                    </span>
                  </div>
                  <div className="mt-2 text-[11px] text-muted-foreground">
                    {platformHealth?.critical_issues?.length ? platformHealth.critical_issues[0] : 'Sem problemas críticos reportados.'}
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
              <h3 className="font-black text-foreground uppercase tracking-tight mb-4">Derived Metrics</h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Request error rate</span>
                  <span className="font-bold text-foreground">{(metrics?.request_error_rate ?? 0).toFixed(4)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Routing fallback rate</span>
                  <span className="font-bold text-foreground">{(metrics?.routing_fallback_rate ?? 0).toFixed(4)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Cache hit ratio</span>
                  <span className="font-bold text-foreground">{((metrics?.cache_hit_ratio ?? 0) * 100).toFixed(1)}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-foreground text-background rounded-3xl p-6 shadow-xl shadow-slate-900/10">
            <h3 className="font-black uppercase tracking-tight mb-6 flex items-center gap-2">
              <ExternalLink className="w-5 h-5 text-primary" />
              Dashboards Externos
            </h3>
            <div className="space-y-2">
              {(dashboardLinks || []).map((link: any) => (
                <a 
                  key={link.name}
                  href={link.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between p-4 rounded-2xl bg-background/10 hover:bg-primary/20 text-background transition-all group"
                >
                  <span className="font-bold text-sm">{link.name}</span>
                  <ExternalLink className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                </a>
              ))}
              {(!dashboardLinks || dashboardLinks.length === 0) && (
                <div className="text-sm text-background/70">
                  Nenhum dashboard externo configurado.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
