import { AlertCircle } from 'lucide-react'
import { VirtualList } from '../../components/table/virtual-list'
import { cn } from '../../lib/utils'

export default function IncidentTimeline() {
  // Simulating large dataset for virtualization demo
  const incidents = Array.from({ length: 1000 }).map((_, i) => ({
    id: `${i}`,
    title: i % 2 === 0 ? 'Latência Elevada em gemma-7b' : 'Interrupção Parcial no Backend',
    description: 'Evento monitorado automaticamente pela infraestrutura de controle.',
    timestamp: new Date(Date.now() - i * 1000 * 60 * 15).toLocaleString(),
    status: i % 3 === 0 ? 'error' : i % 2 === 0 ? 'warning' : 'success',
  }))

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-8">
        <AlertCircle className="w-8 h-8 text-destructive" />
        <h1 className="text-3xl font-black text-foreground">Incident <span className="text-primary">Timeline</span></h1>
      </div>

      <VirtualList
        items={incidents}
        itemHeight={100}
        height="70vh"
        className="bg-transparent border-none shadow-none"
        renderItem={(incident) => (
          <div className="px-6 py-4">
            <div className="flex gap-4">
              <div className="flex flex-col items-center">
                <div className={cn(
                  "w-3 h-3 rounded-full shrink-0 mt-1.5",
                  incident.status === 'error' ? "bg-destructive shadow-[0_0_8px_rgba(239,68,68,0.5)]" :
                  incident.status === 'warning' ? "bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.5)]" :
                  "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"
                )} />
                <div className="w-[1px] flex-1 bg-border my-2" />
              </div>
              <div className="bg-card border border-border rounded-2xl p-4 flex-1 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start mb-1">
                  <h3 className="font-bold text-foreground">{incident.title}</h3>
                  <span className="text-[10px] font-mono text-muted-foreground uppercase">{incident.timestamp}</span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">{incident.description}</p>
              </div>
            </div>
          </div>
        )}
      />
    </div>
  )
}
