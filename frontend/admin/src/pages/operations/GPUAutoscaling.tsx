import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import { Cpu, Activity, Zap, TrendingUp, AlertCircle, Server, BarChart2 } from 'lucide-react'

export default function GPUAutoscaling() {
  const { data: status, isLoading } = useQuery({
    queryKey: ['gpu-autoscaling-status'],
    queryFn: () => api.getGpuAutoscalingStatus()
  })

  const { data: groups } = useQuery({
    queryKey: ['gpu-groups'],
    queryFn: () => api.listGpuGroups()
  })

  if (isLoading) return <div className="p-8">Monitorando GPU Clusters...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">GPU <span className="text-primary">Autoscaling</span></h1>
          <p className="text-muted-foreground font-medium text-lg">Orquestração dinâmica de recursos computacionais para inferência.</p>
        </div>
        <div className={`px-4 py-2 rounded-2xl border flex items-center gap-2 ${
          status?.operational ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-amber-50 text-amber-700 border-amber-100'
        }`}>
          <div className={`w-2 h-2 rounded-full animate-pulse ${status?.operational ? 'bg-emerald-500' : 'bg-amber-500'}`} />
          <span className="text-[10px] font-black uppercase">Service: {status?.operational ? 'Active' : 'Degraded'}</span>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Total GPUs</div>
          <div className="text-3xl font-black text-foreground">{status?.total_gpus || 0}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Utilization</div>
          <div className="text-3xl font-black text-primary">{status?.avg_utilization || 0}%</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Active Nodes</div>
          <div className="text-3xl font-black text-foreground">{status?.active_nodes || 0}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Pending Jobs</div>
          <div className="text-3xl font-black text-amber-600">{status?.pending_jobs || 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1">Autoscaling Groups</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {groups?.map((group: any) => (
              <div key={group.id} className="bg-card border border-border rounded-3xl p-6 hover:border-primary transition-all">
                <div className="flex justify-between items-start mb-4">
                  <div className="p-3 bg-primary/10 text-primary rounded-2xl">
                    <Cpu className="w-6 h-6" />
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] font-black text-muted-foreground uppercase">{group.instance_type}</div>
                    <div className="text-xs font-bold text-foreground">{group.region}</div>
                  </div>
                </div>
                <h3 className="text-xl font-black text-foreground mb-2">{group.name}</h3>
                
                <div className="space-y-4 mb-6">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-muted-foreground">Capacity</span>
                    <span>{group.current_size} / {group.max_size}</span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                    <div 
                      className="bg-primary h-full transition-all" 
                      style={{ width: `${(group.current_size / group.max_size) * 100}%` }}
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-border">
                  <div className="flex items-center gap-2">
                    <Activity className="w-3.5 h-3.5 text-emerald-500" />
                    <span className="text-[10px] font-black text-muted-foreground uppercase">Target: {group.target_utilization}%</span>
                  </div>
                  <button className="text-primary hover:text-primary/80 transition-all text-xs font-bold">
                    Edit Policy
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <h2 className="text-xs font-black text-muted-foreground uppercase tracking-widest px-1">Performance Metrics</h2>
          <div className="bg-card border border-border rounded-3xl p-6 space-y-6">
            <div className="space-y-2">
              <div className="flex justify-between items-end">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Scale-out Latency</div>
                <div className="text-lg font-bold">4.2m</div>
              </div>
              <div className="h-12 bg-primary/5 rounded-lg flex items-end gap-1 p-2">
                {[4,6,3,8,4,5,7,3,5,6,4,8].map((h, i) => (
                  <div key={i} className="flex-1 bg-primary/20 rounded-t-sm" style={{ height: `${h * 10}%` }} />
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-end">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Cold Start Rate</div>
                <div className="text-lg font-bold text-amber-600">12.4%</div>
              </div>
              <div className="h-12 bg-amber-500/5 rounded-lg flex items-end gap-1 p-2">
                {[2,3,5,4,2,6,8,4,3,2,5,4].map((h, i) => (
                  <div key={i} className="flex-1 bg-amber-500/20 rounded-t-sm" style={{ height: `${h * 10}%` }} />
                ))}
              </div>
            </div>

            <div className="pt-4 border-t border-border">
              <div className="flex items-center gap-2 text-destructive mb-2">
                <AlertCircle className="w-4 h-4" />
                <span className="text-[10px] font-black uppercase tracking-widest">Alerta de Quota</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                O cluster <strong>us-east-1</strong> atingiu 90% da quota de instâncias A100. Novos scale-outs podem falhar.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
