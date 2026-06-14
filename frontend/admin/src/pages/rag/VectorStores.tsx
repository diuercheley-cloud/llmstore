import { useQuery, useMutation } from '@tanstack/react-query'
import { Database, Zap, Activity, ShieldCheck, Loader2, PlayCircle, AlertCircle } from 'lucide-react'
import api from '../../lib/api'
import { toast } from 'sonner'

export default function VectorStores() {
  const health = useQuery({
    queryKey: ['vectorstores-health'],
    queryFn: () => api.listVectorStores(),
  })

  const providerInfo = useQuery({
    queryKey: ['vectorstores-provider'],
    queryFn: () => api.getVectorStoreProvider(),
  })

  const testMutation = useMutation({
    mutationFn: (provider: string) => api.testVectorStoreConnection(provider),
    onSuccess: (data) => {
      if (data.status === 'healthy' || data.connected) {
        toast.success('Conexão bem sucedida!')
      } else {
        toast.error('Falha na conexão: ' + (data.detail || 'Status unhealthy'))
      }
      health.refetch()
    },
    onError: (err: any) => toast.error('Erro ao testar conexão: ' + (err?.message || 'Erro desconhecido'))
  })

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-3xl font-black text-foreground flex items-center gap-3">
          <Database className="w-8 h-8 text-primary" /> Vector Stores
        </h1>
        <p className="text-muted-foreground mt-1">Health e configuração de provedores de busca vetorial para RAG e Memória Longa.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/5 font-black uppercase text-xs tracking-wider">
              <span>Provedores Disponíveis</span>
              <Activity className="w-4 h-4 text-muted-foreground" />
            </div>
            <div className="divide-y divide-border">
              {health.isLoading ? (
                <div className="p-12 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
              ) : health.data ? (
                Object.entries(health.data).map(([name, status]: [string, any]) => (
                  <div key={name} className="flex items-center justify-between p-6 hover:bg-secondary/5 transition-colors">
                    <div className="flex items-center gap-4">
                      <div className={`p-3 rounded-2xl ${status.status === 'healthy' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}`}>
                        <Database size={24} />
                      </div>
                      <div>
                        <div className="font-black text-lg capitalize">{name}</div>
                        <div className="text-xs text-muted-foreground font-mono">
                          {status.version ? `v${status.version} · ` : ''}
                          {status.collections_count ?? 0} collections
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      <span className={`badge ${status.status === 'healthy' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                        {status.status.toUpperCase()}
                      </span>
                      <button 
                        onClick={() => testMutation.mutate(name)}
                        disabled={testMutation.isPending}
                        className="p-2 hover:bg-secondary rounded-xl text-muted-foreground hover:text-primary transition-colors"
                        title="Test Connection"
                      >
                        {testMutation.isPending && testMutation.variables === name ? <Loader2 className="w-5 h-5 animate-spin" /> : <PlayCircle className="w-5 h-5" />}
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-12 text-center text-muted-foreground italic flex flex-col items-center gap-4">
                  <AlertCircle className="w-12 h-12 opacity-20" />
                  Nenhum provedor de busca vetorial configurado ou ativo.
                </div>
              )}
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div className="p-6 rounded-3xl border border-border bg-card space-y-4 shadow-sm">
                <h3 className="font-black flex items-center gap-2"><Zap className="w-5 h-5 text-primary" /> Active Config</h3>
                <div className="space-y-4">
                   <div className="p-4 rounded-2xl bg-secondary/20 border border-border/50">
                      <div className="text-[10px] uppercase font-black text-muted-foreground mb-1">Default Provider</div>
                      <div className="text-xl font-black text-primary capitalize">{providerInfo.data?.provider || 'Loading...'}</div>
                   </div>
                   <div className="grid grid-cols-3 gap-2">
                      {['qdrant', 'milvus', 'weaviate'].map(p => (
                         <div key={p} className={`text-center p-2 rounded-xl border text-[10px] font-black uppercase ${providerInfo.data?.[`${p}_enabled`] ? 'bg-emerald-50 border-emerald-100 text-emerald-700' : 'bg-slate-50 border-slate-100 text-slate-400 opacity-50'}`}>
                            {p}
                         </div>
                      ))}
                   </div>
                </div>
             </div>

             <div className="p-6 rounded-3xl border border-border bg-card space-y-4 shadow-sm border-t-4 border-t-primary">
                <h3 className="font-black flex items-center gap-2"><ShieldCheck className="w-5 h-5 text-emerald-500" /> Vector Governance</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                   Garantia de isolamento por tenant ao nível de namespace vetorial. 
                   Sincronização automática habilitada para documentos RAG aprovados.
                </p>
                <div className="pt-2">
                   <button className="text-xs font-black text-primary bg-primary/10 px-3 py-1.5 rounded-lg hover:bg-primary/20 transition-colors">View indexing logs</button>
                </div>
             </div>
          </div>
        </div>

        <div className="space-y-6">
           <div className="bg-slate-950 text-white rounded-3xl p-6 space-y-6 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-primary/20 rounded-full blur-3xl -mr-16 -mt-16" />
              <h3 className="font-black text-lg flex items-center gap-2 relative z-10"><Database className="w-5 h-5" /> Storage Stats</h3>
              
              <div className="space-y-4 relative z-10">
                 <div className="flex justify-between items-end">
                    <span className="text-xs text-slate-400 font-bold uppercase">Total Vectors</span>
                    <span className="text-2xl font-black">{health.data ? Object.values(health.data).reduce((acc: number, curr: any) => acc + (curr.vectors_count ?? 0), 0).toLocaleString() : '—'}</span>
                 </div>
                 <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                    <div className="h-full bg-primary w-2/3" />
                 </div>
                 
                 <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/10">
                    <div>
                       <div className="text-[10px] text-slate-500 font-black uppercase">Dimensions</div>
                       <div className="text-lg font-black">1536 (Ada)</div>
                    </div>
                    <div>
                       <div className="text-[10px] text-slate-500 font-black uppercase">Latency avg</div>
                       <div className="text-lg font-black">12ms</div>
                    </div>
                 </div>
              </div>
           </div>
           
           <div className="p-6 rounded-3xl bg-blue-50 border border-blue-100 space-y-3">
              <h4 className="font-black text-blue-900 text-sm flex items-center gap-2"><Activity className="w-4 h-4" /> Optimization Tip</h4>
              <p className="text-xs text-blue-700 leading-relaxed">
                 Considere habilitar <strong>HNSW indexing</strong> para coleções com mais de 1 milhão de vetores para manter latência sub-100ms.
              </p>
           </div>
        </div>
      </div>
    </div>
  )
}
