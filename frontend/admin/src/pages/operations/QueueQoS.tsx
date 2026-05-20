import { Layers, Zap, Clock, ShieldAlert } from 'lucide-react'
import HealthCard from '../../components/operations/HealthCard'

export default function QueueQoS() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-black text-foreground mb-8">Queue / <span className="text-primary">QoS</span></h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <HealthCard 
          title="Fila Global" 
          value="0" 
          icon={<Layers className="w-6 h-6" />}
          description="Requisições aguardando processamento."
        />
        <HealthCard 
          title="Throughput" 
          value="142 tps" 
          icon={<Zap className="w-6 h-6" />}
          description="Tokens processados por segundo."
        />
        <HealthCard 
          title="Latência Média" 
          value="450ms" 
          icon={<Clock className="w-6 h-6" />}
          description="Tempo de resposta (p50)."
        />
      </div>

      <div className="bg-card border border-border rounded-3xl p-8 shadow-sm">
        <div className="flex items-center gap-3 mb-6">
          <ShieldAlert className="w-6 h-6 text-primary" />
          <h3 className="text-xl font-bold text-foreground">Políticas de Prioridade (QoS)</h3>
        </div>
        
        <div className="space-y-4">
          {[
            { tier: 'Admin', priority: 100, waiting: 0, active: 4, limit: 10 },
            { tier: 'Premium', priority: 50, waiting: 0, active: 8, limit: 20 },
            { tier: 'Basic', priority: 10, waiting: 0, active: 2, limit: 5 },
            { tier: 'Free', priority: 0, waiting: 0, active: 0, limit: 2 },
          ].map((item) => (
            <div key={item.tier} className="p-4 bg-secondary rounded-2xl flex items-center justify-between">
              <div>
                <div className="font-bold text-foreground">{item.tier}</div>
                <div className="text-[10px] font-black text-muted-foreground uppercase">Prioridade: {item.priority}</div>
              </div>
              <div className="flex gap-8">
                 <div className="text-center">
                   <div className="text-xs font-bold text-muted-foreground uppercase mb-1">Active</div>
                   <div className="text-lg font-black text-foreground">{item.active}</div>
                 </div>
                 <div className="text-center">
                   <div className="text-xs font-bold text-muted-foreground uppercase mb-1">Waiting</div>
                   <div className="text-lg font-black text-foreground">{item.waiting}</div>
                 </div>
                 <div className="text-center">
                   <div className="text-xs font-bold text-muted-foreground uppercase mb-1">Limit</div>
                   <div className="text-lg font-black text-foreground">{item.limit}</div>
                 </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
