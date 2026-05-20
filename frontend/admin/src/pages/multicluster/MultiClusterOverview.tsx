import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { Server, Globe, Shield, Activity, Plus, MoreVertical, Power, Construction, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function MultiClusterOverview() {
  const queryClient = useQueryClient()
  
  const { data: clusters, isLoading } = useQuery({
    queryKey: ['clusters'],
    queryFn: async () => {
      const res = await api.get('/admin/clusters')
      return res.data
    }
  })

  const maintenanceMutation = useMutation({
    mutationFn: async (id: string) => api.post(`/admin/clusters/${id}/maintenance`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['clusters'] })
  })

  const resumeMutation = useMutation({
    mutationFn: async (id: string) => api.post(`/admin/clusters/${id}/resume`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['clusters'] })
  })

  if (isLoading) return <div className="p-8">Carregando clusters...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Multi-Cluster <span className="text-indigo-600">Control</span></h1>
          <p className="text-muted-foreground font-medium">Orquestração e saúde de clusters e appliances remotos.</p>
        </div>
        <button className="bg-indigo-600 text-white px-6 py-2.5 rounded-2xl font-bold text-sm flex items-center gap-2 hover:bg-indigo-700 transition-colors">
          <Plus className="w-4 h-4" />
          Registrar Cluster
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {clusters?.map((cluster: any) => (
          <div key={cluster.id} className="bg-card border border-border rounded-3xl p-6 shadow-sm hover:shadow-xl transition-all group">
            <div className="flex justify-between items-start mb-6">
              <div className={`p-4 rounded-2xl ${
                cluster.status === 'active' ? 'bg-indigo-50 text-indigo-600' : 
                cluster.status === 'maintenance' ? 'bg-yellow-500/10 text-yellow-600' : 'bg-destructive/10 text-destructive'
              }`}>
                <Server className="w-6 h-6" />
              </div>
              <div className="flex gap-2">
                <span className={`px-2 py-1 rounded text-[10px] font-black uppercase tracking-tighter ${
                  cluster.status === 'active' ? 'bg-primary/20 text-primary' : 'bg-yellow-500/20 text-yellow-600'
                }`}>
                  {cluster.status}
                </span>
                <span className="bg-secondary text-muted-foreground text-[10px] font-black px-2 py-1 rounded uppercase tracking-tighter">
                  {cluster.cluster_type}
                </span>
              </div>
            </div>

            <h3 className="text-2xl font-black text-foreground mb-1">{cluster.name}</h3>
            <div className="flex items-center gap-1.5 text-muted-foreground text-xs font-medium mb-6">
              <Globe className="w-3.5 h-3.5" />
              {cluster.location || 'Local Data Center'}
              <span className="mx-1">•</span>
              <code className="text-[10px]">{cluster.base_url}</code>
            </div>

            <div className="bg-secondary rounded-2xl p-4 mb-8 grid grid-cols-2 gap-4">
               <div>
                  <div className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-1">Health</div>
                  <div className="flex items-center gap-1.5 text-primary font-bold">
                    <Activity className="w-3.5 h-3.5" />
                    98%
                  </div>
               </div>
               <div>
                  <div className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-1">Sync</div>
                  <div className="flex items-center gap-1.5 text-indigo-600 font-bold">
                    <RefreshCw className="w-3.5 h-3.5" />
                    OK
                  </div>
               </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {cluster.status === 'active' ? (
                <button 
                  onClick={() => maintenanceMutation.mutate(cluster.id)}
                  className="flex items-center justify-center gap-2 bg-yellow-500/10 text-yellow-600 font-bold py-2.5 rounded-xl text-xs hover:bg-yellow-500/20 transition-colors"
                >
                  <Construction className="w-4 h-4" />
                  Manutenção
                </button>
              ) : (
                <button 
                  onClick={() => resumeMutation.mutate(cluster.id)}
                  className="flex items-center justify-center gap-2 bg-primary/10 text-primary font-bold py-2.5 rounded-xl text-xs hover:bg-primary/20 transition-colors"
                >
                  <Power className="w-4 h-4" />
                  Retomar
                </button>
              )}
              <Link 
                to={`/multicluster/clusters/${cluster.id}`}
                className="flex items-center justify-center bg-foreground text-white font-bold py-2.5 rounded-xl text-xs hover:bg-foreground transition-colors"
              >
                Detalhes
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
