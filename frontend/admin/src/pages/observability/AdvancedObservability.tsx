import { useQuery, useMutation } from '@tanstack/react-query'
import api from '../../lib/api'
import { Activity, Zap, AlertTriangle, TrendingUp, DollarSign, Brain, ShieldCheck, Play, Info, Search, Database } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

export default function AdvancedObservability() {
  const [activeTab, setActiveTab] = useState('metrics')

  const { data: metricsData, isLoading: isLoadingMetrics } = useQuery({
    queryKey: ['observability-metrics'],
    queryFn: async () => {
      const res = await api.get('/admin/observability/metrics')
      return res.data
    },
    refetchInterval: 10000
  })

  const { data: anomalies, isLoading: isLoadingAnomalies } = useQuery({
    queryKey: ['observability-anomalies'],
    queryFn: async () => {
      const res = await api.get('/admin/observability/anomalies')
      return res.data
    }
  })

  const summary = metricsData?.summary || {}
  const cards = [
    {
      title: 'Latência Avg',
      value: `${Math.round(summary.average_latency_ms || 0)}ms`,
      icon: <Zap className="w-5 h-5 text-primary" />,
      trend: `${metricsData?.metrics?.length || 0} métricas`,
      status: (summary.average_latency_ms || 0) > 2000 ? 'warning' : 'nominal',
    },
    {
      title: 'Custo Est.',
      value: `$${Number(summary.estimated_cost_usd || 0).toFixed(2)}`,
      icon: <DollarSign className="w-5 h-5 text-primary" />,
      trend: `${summary.cost_window || 'atual'}`,
      status: 'nominal',
    },
    {
      title: 'Tokens/Min',
      value: Number(summary.tokens_per_minute || 0).toLocaleString(),
      icon: <Brain className="w-5 h-5 text-primary" />,
      trend: `${summary.token_window || 'atual'}`,
      status: 'nominal',
    },
    {
      title: 'Anomalias',
      value: String(anomalies?.length || 0),
      icon: <AlertTriangle className="w-5 h-5 text-destructive" />,
      trend: anomalies?.length ? 'ativas' : 'estável',
      status: anomalies?.length > 0 ? 'warning' : 'nominal',
    },
  ]

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-foreground flex items-center gap-3">
            <Activity className="w-8 h-8 text-primary" /> ADVANCED OBSERVABILITY
          </h1>
          <p className="text-muted-foreground mt-1">Monitoramento em tempo real, telemetria eBPF e detecção de anomalias.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {cards.map((card) => (
          <div key={card.title} className="p-6 bg-card border border-border rounded-3xl shadow-sm relative overflow-hidden">
            <div className="flex justify-between items-start mb-4">
              <div className="p-2 bg-secondary/30 rounded-xl">
                {card.icon}
              </div>
              <span className={`text-[10px] font-black px-2 py-0.5 rounded uppercase ${card.status === 'warning' ? 'bg-destructive/10 text-destructive' : 'bg-primary/10 text-primary'}`}>
                {card.status}
              </span>
            </div>
            <div className="text-[10px] font-black text-muted-foreground uppercase mb-1">{card.title}</div>
            <div className="text-2xl font-black">{card.value}</div>
            <div className="text-[9px] font-bold text-muted-foreground mt-2 flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> {card.trend} vs última hora
            </div>
          </div>
        ))}
      </div>

      <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
        <div className="flex border-b border-border bg-secondary/10">
          <button 
            onClick={() => setActiveTab('metrics')}
            className={`px-8 py-4 text-sm font-black tracking-tighter border-b-2 transition-all ${activeTab === 'metrics' ? 'border-primary text-primary bg-primary/5' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
          >
            LIVE METRICS
          </button>
          <button 
            onClick={() => setActiveTab('anomalies')}
            className={`px-8 py-4 text-sm font-black tracking-tighter border-b-2 transition-all ${activeTab === 'anomalies' ? 'border-primary text-primary bg-primary/5' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
          >
            ANOMALY LOG
          </button>
        </div>

        <div className="p-6">
          {activeTab === 'metrics' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {metricsData?.metrics.map((m: any) => (
                  <div key={m.name} className="p-4 bg-secondary/20 border border-border rounded-2xl flex items-center justify-between">
                    <div>
                      <div className="font-bold text-sm uppercase tracking-tight">{m.name}</div>
                      <div className="text-[10px] text-muted-foreground font-mono">Unit: {m.unit} | Type: {m.type}</div>
                    </div>
                    <div className="text-xl font-black text-primary">{m.value}</div>
                  </div>
                ))}
              </div>
              <div className="p-4 bg-primary/5 border border-primary/10 rounded-2xl flex items-center gap-3">
                <Database className="w-5 h-5 text-primary" />
                <div className="text-xs">
                  <span className="font-black uppercase mr-2">eBPF Status:</span>
                  <span className="font-bold text-primary">{metricsData?.ebpf_status}</span>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'anomalies' && (
            <div className="space-y-4">
              {anomalies?.length === 0 ? (
                <div className="p-12 text-center text-muted-foreground italic text-sm">Nenhuma anomalia detectada no período.</div>
              ) : (
                anomalies?.map((a: any) => (
                  <div key={a.id} className="p-4 border border-border rounded-2xl flex items-center gap-4 hover:bg-secondary/10 transition-all">
                    <div className={`p-2 rounded-lg ${a.severity === 'high' ? 'bg-destructive/10 text-destructive' : 'bg-warning/10 text-warning'}`}>
                      <AlertTriangle className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-black text-[10px] uppercase text-primary">{a.metric_name}</span>
                        <span className="text-[10px] font-mono text-muted-foreground">{new Date(a.timestamp).toLocaleTimeString()}</span>
                      </div>
                      <p className="text-sm font-bold">{a.description}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] font-black text-muted-foreground uppercase">Severity</div>
                      <div className={`text-[10px] font-black uppercase ${a.severity === 'high' ? 'text-destructive' : 'text-warning'}`}>{a.severity}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
