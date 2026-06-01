import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { Server, Globe, Activity, Plus, Power, Construction, RefreshCw, X, CheckCircle2, Radar } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useMemo, useState } from 'react'

export default function MultiClusterOverview() {
  const queryClient = useQueryClient()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [form, setForm] = useState({
    name: '',
    cluster_type: 'remote',
    base_url: '',
    location: '',
  })
  
  const { data: clusters, isLoading } = useQuery({
    queryKey: ['clusters'],
    queryFn: async () => {
      const res = await api.get('/admin/clusters')
      return res.data
    }
  })

  const createMutation = useMutation({
    mutationFn: async () => api.post('/admin/clusters', {
      name: form.name.trim(),
      cluster_type: form.cluster_type.trim(),
      base_url: form.base_url.trim(),
      location: form.location.trim() || null,
    }),
    onSuccess: async () => {
      setIsCreateOpen(false)
      setCreateError(null)
      setForm({ name: '', cluster_type: 'remote', base_url: '', location: '' })
      await queryClient.invalidateQueries({ queryKey: ['clusters'] })
    },
    onError: (err: any) => {
      setCreateError(err?.message || 'Falha ao registrar cluster.')
    },
  })

  const maintenanceMutation = useMutation({
    mutationFn: async (id: string) => api.post(`/admin/clusters/${id}/maintenance`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['clusters'] })
  })

  const resumeMutation = useMutation({
    mutationFn: async (id: string) => api.post(`/admin/clusters/${id}/resume`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['clusters'] })
  })

  const stats = useMemo(() => {
    const items = Array.isArray(clusters) ? clusters : []
    return {
      total: items.length,
      active: items.filter((c: any) => c.status === 'active').length,
      maintenance: items.filter((c: any) => c.status === 'maintenance').length,
      degraded: items.filter((c: any) => c.status !== 'active' && c.status !== 'maintenance').length,
    }
  }, [clusters])

  if (isLoading) return <div className="p-8">Carregando clusters...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      <header className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.3em] text-indigo-500 mb-2">Distributed control plane</div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Multi-Cluster <span className="text-indigo-600">Control</span></h1>
          <p className="text-muted-foreground font-medium max-w-2xl">
            Orquestração e saúde de clusters e appliances remotos. Registre instâncias, acompanhe status e coloque nós em manutenção sem sair da página.
          </p>
        </div>
        <button
          onClick={() => {
            setCreateError(null)
            setIsCreateOpen(true)
          }}
          className="bg-indigo-600 text-white px-6 py-2.5 rounded-2xl font-bold text-sm flex items-center gap-2 hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-200"
        >
          <Plus className="w-4 h-4" />
          Registrar Cluster
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Total</div>
          <div className="text-3xl font-black text-foreground">{stats.total}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Ativos</div>
          <div className="text-3xl font-black text-emerald-600">{stats.active}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Manutenção</div>
          <div className="text-3xl font-black text-amber-600">{stats.maintenance}</div>
        </div>
        <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Degradados</div>
          <div className="text-3xl font-black text-rose-600">{stats.degraded}</div>
        </div>
      </div>

      {clusters?.length === 0 ? (
        <div className="bg-card border border-dashed border-border rounded-3xl p-10 text-center">
          <Radar className="w-12 h-12 text-indigo-500 mx-auto mb-4" />
          <h2 className="text-2xl font-black mb-2">Nenhum cluster cadastrado</h2>
          <p className="text-muted-foreground max-w-xl mx-auto mb-6">
            Registre o primeiro cluster para habilitar o controle de manutenção, sincronização e a visão de health da malha distribuída.
          </p>
          <button
            onClick={() => {
              setCreateError(null)
              setIsCreateOpen(true)
            }}
            className="bg-foreground text-background px-5 py-2.5 rounded-xl font-bold"
          >
            Registrar primeiro cluster
          </button>
        </div>
      ) : null}

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
                    {cluster.status === 'active' ? '98%' : cluster.status === 'maintenance' ? '72%' : '41%'}
                  </div>
               </div>
               <div>
                  <div className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-1">Sync</div>
                  <div className="flex items-center gap-1.5 text-indigo-600 font-bold">
                    <RefreshCw className="w-3.5 h-3.5" />
                    {cluster.status === 'active' ? 'OK' : 'Pendente'}
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
                className="flex items-center justify-center bg-foreground text-background font-bold py-2.5 rounded-xl text-xs hover:bg-foreground transition-colors"
              >
                Detalhes
              </Link>
            </div>
          </div>
        ))}
      </div>

      {isCreateOpen ? (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl bg-card border border-border rounded-[2rem] shadow-2xl overflow-hidden">
            <div className="px-6 py-5 border-b border-border flex items-center justify-between">
              <div>
                <div className="text-[10px] font-black uppercase tracking-[0.3em] text-indigo-500 mb-1">Registrar cluster</div>
                <h2 className="text-2xl font-black">Novo cluster remoto</h2>
              </div>
              <button onClick={() => setIsCreateOpen(false)} className="p-2 rounded-full hover:bg-secondary">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid gap-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Nome</label>
                <input
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 outline-none focus:border-indigo-500"
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="Cluster São Paulo"
                />
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                <div className="grid gap-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Tipo</label>
                  <select
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 outline-none focus:border-indigo-500"
                    value={form.cluster_type}
                    onChange={(e) => setForm((prev) => ({ ...prev, cluster_type: e.target.value }))}
                  >
                    <option value="remote">remote</option>
                    <option value="managed">managed</option>
                    <option value="appliance">appliance</option>
                  </select>
                </div>
                <div className="grid gap-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Base URL</label>
                  <input
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 outline-none focus:border-indigo-500"
                    value={form.base_url}
                    onChange={(e) => setForm((prev) => ({ ...prev, base_url: e.target.value }))}
                    placeholder="https://cluster.example.com"
                  />
                </div>
              </div>
              <div className="grid gap-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Localização</label>
                <input
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 outline-none focus:border-indigo-500"
                  value={form.location}
                  onChange={(e) => setForm((prev) => ({ ...prev, location: e.target.value }))}
                  placeholder="sa-east-1"
                />
              </div>

              {createError ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 text-rose-700 px-4 py-3 text-sm font-medium">
                  {createError}
                </div>
              ) : null}
            </div>

            <div className="px-6 py-5 border-t border-border flex items-center justify-end gap-3">
              <button onClick={() => setIsCreateOpen(false)} className="px-4 py-2.5 rounded-xl border border-border font-bold">
                Cancelar
              </button>
              <button
                onClick={() => createMutation.mutate()}
                disabled={!form.name.trim() || !form.base_url.trim() || createMutation.isPending}
                className="px-4 py-2.5 rounded-xl bg-indigo-600 text-white font-bold disabled:opacity-50 flex items-center gap-2"
              >
                {createMutation.isPending ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 animate-pulse" />
                    Registrando...
                  </>
                ) : (
                  'Registrar'
                )}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
