import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { Plus, Search, Box, CheckCircle2, XCircle, Settings2, MoreHorizontal, Database, RefreshCw, Zap, RotateCcw, Trash2 } from 'lucide-react'
import { useState } from 'react'

interface Model {
  id: string
  display_name: string
  name: string // Some versions might use name, keeping for safety or adding if missing
  provider: string
  is_enabled: boolean
  is_active: boolean
  is_default: boolean
  context_length: number
  pricing_unit: string
  input_price: number
  output_price: number
  model_id: string // From registry
  inference_backend_id: string
  model_file: string
}

interface ModelRuntimeInstance {
  id: string
  model_id: string
  backend_id: string
  model_path: string
  port: number
  status: 'loading' | 'ready' | 'failed' | 'unloading' | 'stopped'
  is_active: boolean
  health_status: string
  last_error: string | null
}

export default function Models() {
  const [search, setSearch] = useState('')
  const queryClient = useQueryClient()

  const { data: models, isLoading } = useQuery<Model[]>({
    queryKey: ['models'],
    queryFn: async () => {
      const res = await api.get('/admin/models')
      return res.data
    }
  })

  const { data: runtimes } = useQuery<ModelRuntimeInstance[]>({
    queryKey: ['model-runtimes'],
    queryFn: async () => {
      const res = await api.get('/admin/models/runtime')
      return res.data
    },
    refetchInterval: 5000
  })

  const loadMutation = useMutation({
    mutationFn: async ({ model_id, backend_id, model_path }: { model_id: string, backend_id: string, model_path: string }) => {
      return api.post('/admin/models/runtime/load', { model_id, backend_id, model_path })
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['model-runtimes'] })
  })

  const activateMutation = useMutation({
    mutationFn: async (instance_id: string) => {
      return api.post(`/admin/models/runtime/activate/${instance_id}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['model-runtimes'] })
  })

  const rollbackMutation = useMutation({
    mutationFn: async ({ model_id, backend_id }: { model_id: string, backend_id: string }) => {
      return api.post('/admin/models/runtime/rollback', { model_id, backend_id })
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['model-runtimes'] })
  })

  const unloadMutation = useMutation({
    mutationFn: async (instance_id: string) => {
      return api.post(`/admin/models/runtime/unload/${instance_id}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['model-runtimes'] })
  })

  const toggleMutation = useMutation({
    mutationFn: async ({ id, enabled }: { id: string, enabled: boolean }) => {
      const action = enabled ? 'disable' : 'enable'
      return api.post(`/admin/models/${id}/${action}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['models'] })
  })

  const filtered = models?.filter(m => 
    m.name.toLowerCase().includes(search.toLowerCase()) || 
    m.id.toLowerCase().includes(search.toLowerCase())
  )

  const getRuntimesForModel = (modelId: string) => runtimes?.filter(r => r.model_id === modelId) || []

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Catálogo de Modelos</h1>
          <p className="text-slate-500">Configuração de LLMs, precificação e roteamento padrão.</p>
        </div>
        <button className="bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-xl font-bold flex items-center gap-2 transition-colors shadow-lg shadow-teal-600/20">
          <Plus className="w-5 h-5" />
          Registrar Modelo
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-2">Total de Modelos</div>
          <div className="text-3xl font-black text-slate-900">{models?.length || 0}</div>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-2">Ativos</div>
          <div className="text-3xl font-black text-teal-600">{models?.filter(m => m.is_active).length || 0}</div>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-2">Providers</div>
          <div className="text-3xl font-black text-slate-900">{new Set(models?.map(m => m.provider)).size || 0}</div>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-2">Runtimes</div>
          <div className="text-3xl font-black text-amber-500">{runtimes?.filter(r => r.status === 'ready').length || 0}</div>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 bg-slate-50/50 flex gap-4">
          <div className="relative flex-1">
            <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              placeholder="Filtrar por nome, ID ou provider..."
              className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-teal-500 outline-none transition-all"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-slate-400 text-xs font-bold uppercase tracking-widest bg-slate-50/50">
                <th className="px-6 py-4">Modelo</th>
                <th className="px-6 py-4">Hot Swap / Runtime</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Capacidade</th>
                <th className="px-6 py-4">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading && (
                <tr><td colSpan={5} className="px-6 py-20 text-center">
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin"></div>
                    <span className="text-slate-400 font-medium">Carregando catálogo...</span>
                  </div>
                </td></tr>
              )}
              {filtered?.map(model => {
                const modelRuntimes = getRuntimesForModel(model.id)
                const activeRuntime = modelRuntimes.find(r => r.is_active)
                
                return (
                  <tr key={model.id} className="hover:bg-slate-50/80 transition-colors group">
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-slate-100 text-slate-500 rounded-lg group-hover:bg-teal-50 group-hover:text-teal-600 transition-colors">
                          <Box className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="font-bold text-slate-900 flex items-center gap-2">
                            {model.display_name || model.name}
                            {model.is_default && <span className="px-2 py-0.5 bg-teal-100 text-teal-700 text-[10px] font-black uppercase rounded-md tracking-tighter">Default</span>}
                          </div>
                          <div className="text-xs font-mono text-slate-400">{model.model_id}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      {model.provider === 'llama.cpp' ? (
                        <div className="flex flex-col gap-2">
                          {activeRuntime ? (
                            <div className="flex items-center gap-2 text-xs">
                              <Zap className="w-3 h-3 text-amber-500 fill-amber-500" />
                              <span className="font-bold text-slate-700">Ativo: Port {activeRuntime.port}</span>
                              <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded font-black uppercase text-[9px]">Ready</span>
                            </div>
                          ) : (
                            <span className="text-xs text-slate-400 italic">Nenhum runtime ativo</span>
                          )}
                          <div className="flex gap-2">
                            <button 
                              onClick={() => loadMutation.mutate({ model_id: model.id, backend_id: model.inference_backend_id, model_path: model.model_file })}
                              disabled={loadMutation.isPending}
                              className="text-[10px] font-bold bg-slate-100 hover:bg-teal-100 text-slate-600 hover:text-teal-700 px-2 py-1 rounded transition-colors flex items-center gap-1"
                            >
                              <RefreshCw className={`w-3 h-3 ${loadMutation.isPending ? 'animate-spin' : ''}`} />
                              LOAD NEW
                            </button>
                            {modelRuntimes.filter(r => !r.is_active && r.status === 'ready').length > 0 && (
                              <button 
                                onClick={() => activateMutation.mutate(modelRuntimes.find(r => !r.is_active && r.status === 'ready')!.id)}
                                className="text-[10px] font-bold bg-amber-100 hover:bg-amber-200 text-amber-700 px-2 py-1 rounded transition-colors flex items-center gap-1"
                              >
                                <Zap className="w-3 h-3" />
                                ACTIVATE
                              </button>
                            )}
                            {activeRuntime && (
                              <button 
                                onClick={() => rollbackMutation.mutate({ model_id: model.id, backend_id: model.inference_backend_id })}
                                className="text-[10px] font-bold bg-rose-100 hover:bg-rose-200 text-rose-700 px-2 py-1 rounded transition-colors flex items-center gap-1"
                              >
                                <RotateCcw className="w-3 h-3" />
                                ROLLBACK
                              </button>
                            )}
                          </div>
                          {modelRuntimes.filter(r => r.status === 'loading').length > 0 && (
                            <div className="text-[9px] text-amber-600 font-bold animate-pulse">Carregando novo runtime...</div>
                          )}
                          {modelRuntimes.filter(r => r.status === 'failed').map(r => (
                            <div key={r.id} className="text-[9px] text-rose-600 font-medium">Erro: {r.last_error?.substring(0, 40)}...</div>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">Hot swap não suportado</span>
                      )}
                    </td>
                    <td className="px-6 py-5">
                      <button 
                        onClick={() => toggleMutation.mutate({ id: model.id, enabled: model.is_active })}
                        disabled={toggleMutation.isPending}
                        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold transition-all ${
                          model.is_active 
                            ? 'bg-green-100 text-green-700 hover:bg-green-200' 
                            : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                        }`}
                      >
                        {model.is_active ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                        {model.is_active ? 'ATIVO' : 'DESATIVADO'}
                      </button>
                    </td>
                    <td className="px-6 py-5">
                      <div className="text-sm font-semibold text-slate-700">{(model.context_length / 1024).toFixed(0)}k ctx</div>
                      <div className="text-xs text-slate-400 font-medium uppercase tracking-tight">{model.provider}</div>
                    </td>
                    <td className="px-6 py-5">
                      <div className="flex gap-2">
                        <button className="p-2 hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 rounded-xl text-slate-600 transition-all"><Settings2 className="w-4 h-4" /></button>
                        <button className="p-2 hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 rounded-xl text-slate-600 transition-all"><Database className="w-4 h-4" /></button>
                        <button className="p-2 hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 rounded-xl text-slate-600 transition-all"><MoreHorizontal className="w-4 h-4" /></button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
