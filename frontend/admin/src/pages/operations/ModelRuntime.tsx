import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import { Box, Zap, RotateCcw, Activity } from 'lucide-react'
import StatusBadge from '../../components/operations/StatusBadge'
import ActionPanel from '../../components/operations/ActionPanel'

export default function ModelRuntime() {
  const { data: models } = useQuery({
    queryKey: ['models'],
    queryFn: async () => {
      const res = await api.get('/admin/models')
      return res.data
    }
  })

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-black text-foreground mb-8">Model <span className="text-primary">Runtime</span></h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        {models?.map((model: any) => (
          <div key={model.id} className="bg-card border border-border rounded-3xl p-6 shadow-sm">
            <div className="flex justify-between items-start mb-4">
              <div className="p-3 bg-secondary text-muted-foreground rounded-2xl">
                <Box className="w-6 h-6" />
              </div>
              <StatusBadge status={model.is_active ? 'healthy' : 'error'} />
            </div>
            <h3 className="text-lg font-bold text-foreground mb-1">{model.display_name}</h3>
            <p className="text-xs font-mono text-muted-foreground mb-6">{model.model_id}</p>
            
            <div className="space-y-3">
              <div className="flex justify-between text-xs font-bold uppercase tracking-wider">
                <span className="text-muted-foreground">Contexto</span>
                <span className="text-foreground">{model.context_length} tokens</span>
              </div>
              <div className="flex justify-between text-xs font-bold uppercase tracking-wider">
                <span className="text-muted-foreground">Provider</span>
                <span className="text-foreground">{model.provider}</span>
              </div>
            </div>
            
            <div className="mt-8 pt-6 border-t border-border flex gap-2">
              <button className="flex-1 bg-foreground text-background text-xs font-black py-2 rounded-xl hover:bg-foreground transition-colors">
                REDEPLOY
              </button>
              <button className="flex-1 bg-destructive/10 text-destructive text-xs font-black py-2 rounded-xl hover:bg-destructive/20 transition-colors border border-rose-100">
                ROLLBACK
              </button>
            </div>
          </div>
        ))}
      </div>

      <ActionPanel title="Ações Globais de Modelo" description="Controles para todos os runtimes de inferência.">
         <button className="flex items-center gap-2 bg-foreground text-background px-4 py-2 rounded-xl font-bold text-sm">
           <Zap className="w-4 h-4" />
           Ativar Hot-Swap Automático
         </button>
         <button className="flex items-center gap-2 bg-card text-foreground px-4 py-2 rounded-xl font-bold text-sm border border-border">
           <Activity className="w-4 h-4" />
           Resetar Métricas de Performance
         </button>
      </ActionPanel>
    </div>
  )
}
