import { useState } from 'react'
import { Layers, Box, Rocket, ShieldCheck, History, Plus, Search, Filter, Loader2 } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { LoadingCard } from '../../components/ui-feedback'

export default function AdapterRegistry() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('all')

  const { data, isLoading } = useQuery({
    queryKey: ['model-lifecycle'],
    queryFn: () => api.listModelLifecycle()
  })

  const validateMutation = useMutation({
    mutationFn: (id: string) => api.transitionModelLifecycle(id, 'approved'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model-lifecycle'] })
      alert("Modelo validado e aprovado com sucesso!")
    }
  })

  const promoteMutation = useMutation({
    mutationFn: (id: string) => api.transitionModelLifecycle(id, 'promoted'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model-lifecycle'] })
      alert("Modelo promovido para produção!")
    }
  })

  if (isLoading) return <LoadingCard />

  const records = data?.items || []
  const filtered = records.filter((r: any) => {
    if (activeTab === 'all') return true
    if (activeTab === 'production') return r.lifecycle_state === 'promoted'
    if (activeTab === 'staging') return r.lifecycle_state === 'approved' || r.lifecycle_state === 'staged'
    if (activeTab === 'development') return r.lifecycle_state === 'discovered'
    return true
  })

  const handleHistory = (id: string) => {
    alert(`Visualizando histórico de alterações para o artefato: ${id}`)
  }

  const handleDeploy = (id: string) => {
    alert(`Iniciando fluxo de deploy para o nó de runtime... Artefato: ${id}`)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Adapter <span className="text-primary">Registry</span></h1>
          <p className="text-muted-foreground font-medium text-lg">Gestão e promoção de adaptadores LoRA e artefatos de modelos.</p>
        </div>
        <button 
          onClick={() => alert("Funcionalidade de registro manual em breve. Utilize o supply-chain CLI para descoberta automática.")}
          className="bg-primary text-primary-foreground px-6 py-3 rounded-2xl font-bold flex items-center gap-2 hover:opacity-90 transition-all shadow-lg shadow-primary/20"
        >
          <Plus className="w-5 h-5" />
          Registrar Adaptador
        </button>
      </header>

      <div className="flex gap-4 mb-8">
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Buscar artefatos, modelos base ou tags..." 
            className="w-full pl-12 pr-4 py-3 bg-card border border-border rounded-2xl outline-none focus:ring-2 focus:ring-primary/20 transition-all"
          />
        </div>
        <button className="bg-card border border-border px-4 py-3 rounded-2xl font-bold flex items-center gap-2 hover:bg-muted transition-all">
          <Filter className="w-5 h-5" />
          Filtros
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-card border border-border rounded-3xl p-2">
            {['all', 'production', 'staging', 'development'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`w-full text-left px-4 py-3 rounded-2xl text-xs font-black uppercase tracking-widest transition-all ${
                  activeTab === tab ? 'bg-primary text-primary-foreground shadow-md' : 'hover:bg-muted text-muted-foreground'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="bg-primary/5 border border-primary/10 rounded-3xl p-6">
            <h3 className="text-sm font-bold text-primary mb-2 flex items-center gap-2">
              <Rocket className="w-4 h-4" />
              Promotion Flow
            </h3>
            <p className="text-xs text-primary/80 leading-relaxed mb-4">
              Artefatos em staging requerem validação de integridade e assinatura antes de serem promovidos.
            </p>
            <button className="w-full py-2 bg-primary text-primary-foreground rounded-xl text-[10px] font-black uppercase tracking-widest">
              Ver Pipeline
            </button>
          </div>
        </div>

        <div className="lg:col-span-3 space-y-6">
          {filtered.map((record: any) => (
            <div key={record.id} className="bg-card border border-border rounded-3xl p-6 hover:border-primary/50 transition-all flex flex-col md:flex-row gap-6">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-muted rounded-xl text-muted-foreground">
                    <Layers className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-xl font-black text-foreground">{record.model_alias || record.model_name}</h3>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Box className="w-3.5 h-3.5" />
                      Name: <span className="font-bold text-foreground">{record.model_name}</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex flex-wrap gap-2 mt-4">
                  <span className="px-2 py-1 bg-muted rounded text-[10px] font-black uppercase text-muted-foreground">Format: {record.model_format}</span>
                  <span className="px-2 py-1 bg-muted rounded text-[10px] font-black uppercase text-muted-foreground">v{record.model_version || '1.0.0'}</span>
                  <span className="px-2 py-1 bg-muted rounded text-[10px] font-black uppercase text-muted-foreground">Cluster: {record.cluster_id || 'local'}</span>
                </div>
              </div>

              <div className="flex md:flex-col justify-between items-end gap-4 min-w-[160px]">
                <span className={`px-3 py-1.5 rounded-full text-[10px] font-black uppercase tracking-tighter ${
                  record.lifecycle_state === 'promoted' ? 'bg-emerald-500/10 text-emerald-600' : 
                  record.lifecycle_state === 'quarantined' ? 'bg-destructive/10 text-destructive' :
                  'bg-amber-500/10 text-amber-600'
                }`}>
                  {record.lifecycle_state}
                </span>
                
                <div className="flex gap-2">
                  <button 
                    onClick={() => handleHistory(record.id)}
                    className="p-2 hover:bg-muted rounded-xl transition-all" 
                    title="History"
                  >
                    <History className="w-5 h-5 text-muted-foreground" />
                  </button>
                  <button 
                    disabled={record.lifecycle_state === 'approved' || record.lifecycle_state === 'promoted'}
                    onClick={() => validateMutation.mutate(record.id)}
                    className="p-2 hover:bg-muted rounded-xl transition-all disabled:opacity-30" 
                    title="Validate & Approve"
                  >
                    {validateMutation.isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : <ShieldCheck className={`w-5 h-5 ${record.lifecycle_state === 'approved' ? 'text-emerald-500' : 'text-muted-foreground'}`} />}
                  </button>
                  <button 
                    onClick={() => record.lifecycle_state === 'approved' ? promoteMutation.mutate(record.id) : handleDeploy(record.id)}
                    className="bg-foreground text-background px-4 py-2 rounded-xl text-xs font-bold hover:opacity-90 transition-all"
                  >
                    {record.lifecycle_state === 'approved' ? 'Promote' : 'Deploy'}
                  </button>
                </div>
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-20 bg-muted/20 rounded-[40px] border border-dashed border-border">
               <Layers className="w-12 h-12 mx-auto mb-4 opacity-20" />
               <p className="font-bold text-muted-foreground">Nenhum adaptador ou artefato encontrado nesta categoria.</p>
               <p className="text-xs text-muted-foreground/60 mt-1">Os modelos são descobertos automaticamente durante o processo de supply chain.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
