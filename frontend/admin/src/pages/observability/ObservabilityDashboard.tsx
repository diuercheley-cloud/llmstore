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

  const { data: metrics } = useQuery({
    queryKey: ['derived-metrics'],
    queryFn: async () => {
      const res = await api.get('/admin/observability/metrics/derived')
      return res.data
    }
  })

  const { data: incidents } = useQuery({
    queryKey: ['incident-timeline'],
    queryFn: async () => {
      const res = await api.get('/admin/observability/incidents/timeline')
      return res.data
    }
  })

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10">
        <h1 className="text-4xl font-black text-foreground tracking-tight">Advanced <span className="text-primary">Observability</span></h1>
        <p className="text-muted-foreground font-medium text-lg">Visibilidade profunda sobre saúde, performance e compliance.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <HealthCard 
          title="Availability (30d)" 
          value={`${errorBudget?.current_availability || '99.9'}%`} 
          status="healthy"
          icon={<Activity className="w-6 h-6" />}
          description="Target: 99.9%"
        />
        <HealthCard 
          title="Error Budget" 
          value={`${errorBudget?.remaining_budget_percent || '85'}%`} 
          status={errorBudget?.remaining_budget_percent < 20 ? 'warning' : 'healthy'}
          icon={<BarChart3 className="w-6 h-6" />}
          description="Orçamento de erro restante."
        />
        <HealthCard 
          title="Burn Rate" 
          value={`${errorBudget?.burn_rate || '1.0'}x`} 
          status={errorBudget?.burn_rate > 2 ? 'warning' : 'healthy'}
          icon={<Clock className="w-6 h-6" />}
          description="Velocidade de consumo do budget."
        />
        <HealthCard 
          title="Reliability Score" 
          value={`${(metrics?.provider_reliability_score * 100).toFixed(1) || '0'}%`} 
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
              {incidents?.map((incident: any) => (
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
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-foreground text-white rounded-3xl p-6 shadow-xl shadow-slate-900/10">
            <h3 className="font-black uppercase tracking-tight mb-6 flex items-center gap-2">
              <ExternalLink className="w-5 h-5 text-primary" />
              Dashboards Externos
            </h3>
            <div className="space-y-2">
              {dashboardLinks?.map((link: any) => (
                <a 
                  key={link.name}
                  href={link.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between p-4 rounded-2xl bg-foreground hover:bg-primary transition-all group"
                >
                  <span className="font-bold text-sm">{link.name}</span>
                  <ExternalLink className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                </a>
              ))}
            </div>
          </div>

          <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
            <h3 className="font-black text-foreground uppercase tracking-tight mb-4">SLO Status</h3>
            <div className="space-y-4">
               <div>
                  <div className="flex justify-between text-xs font-bold mb-1.5">
                    <span className="text-muted-foreground uppercase">Availability Target</span>
                    <span className="text-foreground">99.9%</span>
                  </div>
                  <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
                    <div className="bg-primary h-full w-[99.9%]"></div>
                  </div>
               </div>
               <div>
                  <div className="flex justify-between text-xs font-bold mb-1.5">
                    <span className="text-muted-foreground uppercase">Latency p95 Target</span>
                    <span className="text-foreground">2.0s</span>
                  </div>
                  <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
                    <div className="bg-yellow-500/100 h-full w-[85%]"></div>
                  </div>
               </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
