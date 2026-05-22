import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import HealthCard from '../../components/operations/HealthCard'
import { 
  Bot, 
  Clock, 
  Zap, 
  AlertCircle, 
  Terminal, 
  History, 
  Wrench, 
  ShieldCheck, 
  Ban, 
  Database, 
  Coins,
  ChevronRight,
  ChevronDown,
  Activity
} from 'lucide-react'

export default function AgentObservability() {
  const [selectedRun, setSelectedRun] = useState<string | null>(null)

  const { data: overview } = useQuery({
    queryKey: ['agent-observability-overview'],
    queryFn: async () => {
      const res = await api.get('/admin/agents/observability/overview')
      return res.data
    }
  })

  const { data: metricsSummary } = useQuery({
    queryKey: ['agent-metrics-summary'],
    queryFn: async () => {
      const res = await api.get('/admin/agents/observability/metrics/summary')
      return res.data
    }
  })

  const { data: timeline } = useQuery({
    queryKey: ['agent-run-timeline', selectedRun],
    queryFn: async () => {
      if (!selectedRun) return null
      const res = await api.get(`/admin/agents/observability/runs/${selectedRun}/timeline`)
      return res.data
    },
    enabled: !!selectedRun
  })

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10">
        <h1 className="text-4xl font-black text-foreground tracking-tight">Agent <span className="text-primary">Observability</span></h1>
        <p className="text-muted-foreground font-medium text-lg">Monitoramento detalhado de execuções, ferramentas e autonomia.</p>
      </header>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <HealthCard 
          title="Total Runs" 
          value={overview?.total_runs || '0'} 
          icon={<Bot className="w-6 h-6" />}
          description="Execuções totais registradas."
        />
        <HealthCard 
          title="Avg Step Latency" 
          value={`${(metricsSummary?.avg_step_latency_ms || 0).toFixed(0)}ms`} 
          status={metricsSummary?.avg_step_latency_ms > 2000 ? 'warning' : 'healthy'}
          icon={<Clock className="w-6 h-6" />}
          description="Média de latência por passo."
        />
        <HealthCard 
          title="Total Tokens" 
          value={metricsSummary?.total_tokens?.toLocaleString() || '0'} 
          icon={<Zap className="w-6 h-6" />}
          description="Consumo total de tokens."
        />
        <HealthCard 
          title="Estimated Cost" 
          value={`R$ ${(metricsSummary?.total_cost_brl || 0).toFixed(2)}`} 
          icon={<Coins className="w-6 h-6" />}
          description="Custo total estimado em BRL."
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Runs Table */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
            <div className="p-6 border-b border-border flex justify-between items-center bg-secondary/50">
              <h3 className="font-black text-foreground uppercase tracking-tight">Recent Agent Runs</h3>
              <History className="w-5 h-5 text-muted-foreground" />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-secondary/30 text-muted-foreground text-[10px] font-black uppercase tracking-widest border-b border-border">
                    <th className="px-6 py-3">Run ID</th>
                    <th className="px-6 py-3">Agent</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3">Steps</th>
                    <th className="px-6 py-3">Started At</th>
                    <th className="px-6 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {overview?.recent_runs?.map((run: any) => (
                    <tr 
                      key={run.id} 
                      className={`hover:bg-secondary/50 transition-colors cursor-pointer ${selectedRun === run.id ? 'bg-primary/5' : ''}`}
                      onClick={() => setSelectedRun(run.id)}
                    >
                      <td className="px-6 py-4 font-mono text-xs">{run.id.slice(0, 8)}...</td>
                      <td className="px-6 py-4 font-bold text-sm">{run.agent_id.slice(0, 8)}...</td>
                      <td className="px-6 py-4">
                        <span className={`text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-tighter ${
                          run.status === 'completed' ? 'bg-green-500/10 text-green-600' :
                          run.status === 'failed' ? 'bg-destructive/10 text-destructive' :
                          run.status === 'running' ? 'bg-primary/10 text-primary animate-pulse' :
                          'bg-secondary text-muted-foreground'
                        }`}>
                          {run.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm">{run.total_steps}</td>
                      <td className="px-6 py-4 text-xs text-muted-foreground">{new Date(run.started_at).toLocaleString()}</td>
                      <td className="px-6 py-4 text-right">
                        {selectedRun === run.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </td>
                    </tr>
                  ))}
                  {(!overview?.recent_runs || overview.recent_runs.length === 0) && (
                    <tr>
                      <td colSpan={6} className="px-6 py-10 text-center text-muted-foreground italic">Nenhuma execução recente encontrada.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Timeline View */}
          {selectedRun && (
            <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm animate-in fade-in slide-in-from-bottom-4">
              <div className="p-6 border-b border-border flex justify-between items-center bg-secondary/50">
                <h3 className="font-black text-foreground uppercase tracking-tight">Run Timeline: <span className="text-primary">{selectedRun.slice(0, 8)}</span></h3>
                <Terminal className="w-5 h-5 text-primary" />
              </div>
              <div className="p-6 space-y-6">
                {timeline?.map((item: any, idx: number) => (
                  <div key={idx} className="relative pl-8 before:absolute before:left-[11px] before:top-2 before:bottom-[-24px] before:w-[2px] before:bg-border last:before:hidden">
                    <div className={`absolute left-0 top-1 w-6 h-6 rounded-full flex items-center justify-center border-2 border-background shadow-sm ${
                      item.type === 'step' ? (
                        item.status === 'success' ? 'bg-green-500 text-white' : 'bg-destructive text-white'
                      ) : 'bg-primary text-white'
                    }`}>
                      {item.type === 'step' ? (
                        item.step_type === 'tool_call' ? <Wrench size={12} /> : 
                        item.step_type === 'model_call' ? <Zap size={12} /> :
                        <ChevronRight size={12} />
                      ) : <Activity size={12} />}
                    </div>
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <h4 className="font-bold text-foreground text-sm">
                          {item.type === 'step' ? `Step ${item.step_number}: ${item.step_type}` : `Event: ${item.event_type}`}
                        </h4>
                        <span className="text-[10px] font-mono text-muted-foreground">{new Date(item.timestamp).toLocaleTimeString()}</span>
                      </div>
                      {item.type === 'step' && (
                        <div className="text-xs text-muted-foreground flex gap-4">
                          <span>Status: <span className={item.status === 'success' ? 'text-green-600' : 'text-destructive'}>{item.status}</span></span>
                          {item.latency_ms && <span>Latency: {item.latency_ms}ms</span>}
                        </div>
                      )}
                      {item.error && (
                        <div className="mt-2 p-3 bg-destructive/5 border border-destructive/10 rounded-xl text-destructive text-xs font-mono">
                          {item.error}
                        </div>
                      )}
                      {item.payload && (
                        <pre className="mt-2 p-3 bg-secondary/50 rounded-xl text-[10px] font-mono overflow-x-auto">
                          {JSON.stringify(item.payload, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar Summary */}
        <div className="space-y-6">
          <div className="bg-foreground text-white rounded-3xl p-6 shadow-xl">
            <h3 className="font-black uppercase tracking-tight mb-6 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-primary" />
              Guardrails Status
            </h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 rounded-2xl bg-white/5">
                <div className="flex items-center gap-3">
                  <Ban className="w-4 h-4 text-destructive" />
                  <span className="text-sm font-bold">Policy Denials</span>
                </div>
                <span className="text-xs font-mono">0</span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-2xl bg-white/5">
                <div className="flex items-center gap-3">
                  <Database className="w-4 h-4 text-primary" />
                  <span className="text-sm font-bold">Memory Writes</span>
                </div>
                <span className="text-xs font-mono">0</span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-2xl bg-white/5">
                <div className="flex items-center gap-3">
                  <AlertCircle className="w-4 h-4 text-yellow-500" />
                  <span className="text-sm font-bold">Tool Failures</span>
                </div>
                <span className="text-xs font-mono">0</span>
              </div>
            </div>
          </div>

          <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
            <h3 className="font-black text-foreground uppercase tracking-tight mb-4">Quick Stats</h3>
            <div className="space-y-4">
               <div>
                  <div className="flex justify-between text-xs font-bold mb-1.5">
                    <span className="text-muted-foreground uppercase">Success Rate</span>
                    <span className="text-foreground">
                      {overview?.status_distribution?.completed ? 
                        ((overview.status_distribution.completed / overview.total_runs) * 100).toFixed(1) : '100'}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
                    <div className="bg-primary h-full w-[95%]"></div>
                  </div>
               </div>
               <div className="pt-2">
                 <h4 className="text-[10px] font-black uppercase text-muted-foreground mb-3 tracking-widest">Status Distribution</h4>
                 <div className="space-y-2">
                   {overview?.status_distribution && Object.entries(overview.status_distribution).map(([status, count]: [string, any]) => (
                     <div key={status} className="flex justify-between items-center text-xs">
                       <span className="capitalize">{status}</span>
                       <span className="font-mono font-bold">{count}</span>
                     </div>
                   ))}
                 </div>
               </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
