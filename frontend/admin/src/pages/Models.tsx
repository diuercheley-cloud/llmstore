import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { Plus, Box, CheckCircle2, XCircle, Settings2, Database, RefreshCw, Zap, Power, PowerOff, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { AdvancedTable } from '../components/table/advanced-table'
import { toast } from 'sonner'
import type { ColumnDef } from '@tanstack/react-table'

interface Model {
  id: string
  display_name: string
  model_id: string
  provider: string
  is_active: boolean
  is_default: boolean
  context_length: number
  pricing_unit: string
  input_price: number
  output_price: number
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

interface BackendOption {
  id: string
  name: string
  provider: string
  backend_url: string
  is_active: boolean
}

export default function Models() {
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 10 })
  const [filters, setFilters] = useState<any>({})
  const [sorting, setSorting] = useState<any[]>([])
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState({
    display_name: '',
    model_id: '',
    model_alias: '',
    inference_backend_id: '',
    provider: 'llama.cpp',
    model_file: '',
    context_length: 4096,
    is_active: true,
    is_default: false,
    status: 'configured',
    allow_reasoning: true,
    include_reasoning_default: false,
    prompt_template: '',
  })
  const queryClient = useQueryClient()

  const { data: modelsData, isLoading: isLoadingModels } = useQuery({
    queryKey: ['models', pagination, filters, sorting],
    queryFn: async () => {
      const res = await api.get('/admin/models', {
        params: {
          page: pagination.pageIndex + 1,
          limit: pagination.pageSize,
          ...filters
        }
      })
      if (Array.isArray(res.data)) return { items: res.data, total: res.data.length }
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

  const { data: backendsData } = useQuery<{ items?: BackendOption[] } | BackendOption[]>({
    queryKey: ['backends-options'],
    queryFn: async () => {
      const res = await api.get('/admin/backends', { params: { page: 1, limit: 200 } })
      return res.data
    }
  })

  const backendOptions = Array.isArray(backendsData) ? backendsData : (backendsData?.items || [])

  const toggleMutation = useMutation({
    mutationFn: async ({ id, enabled }: { id: string, enabled: boolean }) => {
      const action = enabled ? 'disable' : 'enable'
      return api.post(`/admin/models/${id}/${action}`)
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['models'] })
      toast.success(`Modelo ${variables.enabled ? 'desativado' : 'ativado'} com sucesso!`)
    }
  })

  const createModelMutation = useMutation({
    mutationFn: async () => {
      const payload: Record<string, any> = {
        display_name: createForm.display_name.trim() || null,
        model_id: createForm.model_id.trim(),
        model_alias: createForm.model_alias.trim() || null,
        inference_backend_id: createForm.inference_backend_id || null,
        provider: createForm.provider,
        model_file: createForm.model_file.trim(),
        context_length: Number(createForm.context_length) || 4096,
        is_active: createForm.is_active,
        is_default: createForm.is_default,
        status: createForm.status,
        allow_reasoning: createForm.allow_reasoning,
        include_reasoning_default: createForm.include_reasoning_default,
        prompt_template: createForm.prompt_template.trim() || null,
      }
      const res = await api.post('/admin/models', payload)
      return res.data as Model
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] })
      setIsCreateOpen(false)
      setCreateForm({
        display_name: '',
        model_id: '',
        model_alias: '',
        inference_backend_id: '',
        provider: 'llama.cpp',
        model_file: '',
        context_length: 4096,
        is_active: true,
        is_default: false,
        status: 'configured',
        allow_reasoning: true,
        include_reasoning_default: false,
        prompt_template: '',
      })
      toast.success('Modelo registrado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Falha ao registrar modelo')
    }
  })

  const getRuntimesForModel = (modelId: string) => runtimes?.filter(r => r.model_id === modelId) || []

  const columns: ColumnDef<Model>[] = [
    {
      accessorKey: 'display_name',
      header: 'Modelo',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="p-2 bg-secondary rounded-lg">
            <Box className="w-4 h-4 text-primary" />
          </div>
          <div>
            <div className="font-bold text-foreground">{row.original.display_name}</div>
            <div className="text-[10px] font-mono text-muted-foreground">{row.original.model_id}</div>
          </div>
        </div>
      )
    },
    {
      accessorKey: 'provider',
      header: 'Provider',
      cell: ({ row }) => (
        <span className="px-2 py-0.5 bg-secondary text-muted-foreground text-[10px] font-black rounded-md uppercase">
          {row.original.provider}
        </span>
      )
    },
    {
      id: 'runtime',
      header: 'Runtime Status',
      cell: ({ row }) => {
        const modelRuntimes = getRuntimesForModel(row.original.id)
        const activeRuntime = modelRuntimes.find(r => r.is_active)
        return (
          <div className="flex flex-col gap-1">
            {activeRuntime ? (
              <span className="inline-flex items-center gap-1 text-emerald-600 text-[10px] font-black uppercase">
                <Zap className="w-3 h-3" /> {activeRuntime.status}
              </span>
            ) : (
              <span className="text-muted-foreground text-[10px] font-black uppercase tracking-tight">Standby</span>
            )}
          </div>
        )
      }
    },
    {
      accessorKey: 'is_active',
      header: 'Estado',
      cell: ({ row }) => row.original.is_active ? (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-500/10 text-emerald-600 text-[10px] font-black rounded-md">
          <CheckCircle2 className="w-3 h-3" /> ONLINE
        </span>
      ) : (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-secondary text-muted-foreground text-[10px] font-black rounded-md">
          <XCircle className="w-3 h-3" /> OFFLINE
        </span>
      )
    },
    {
      id: 'actions',
      header: 'Ações',
      cell: ({ row }) => (
        <div className="flex gap-2 justify-end">
          <button 
            onClick={() => toggleMutation.mutate({ id: row.original.id, enabled: row.original.is_active })}
            className="p-2 hover:bg-secondary rounded-lg text-muted-foreground transition-all"
          >
            {row.original.is_active ? <PowerOff className="w-4 h-4" /> : <Power className="w-4 h-4 text-primary" />}
          </button>
          <button className="p-2 hover:bg-secondary rounded-lg text-muted-foreground transition-all">
            <Settings2 className="w-4 h-4" />
          </button>
        </div>
      ),
      enableHiding: false,
    }
  ]

  const batchActions = [
    {
      label: 'Habilitar Selecionados',
      icon: <Power size={14} />,
      onClick: (rows: Model[]) => toast.success(`${rows.length} modelos habilitados`),
    },
    {
      label: 'Desabilitar Selecionados',
      icon: <PowerOff size={14} />,
      onClick: (rows: Model[]) => toast.success(`${rows.length} modelos desabilitados`),
      variant: 'destructive' as const
    },
    {
      label: 'Excluir Registros',
      icon: <Trash2 size={14} />,
      onClick: (rows: Model[]) => toast.error('Exclusão de modelos não permitida via lote.'),
      variant: 'destructive' as const
    }
  ]

  const filterConfig = [
    { id: 'display_name', label: 'Nome do Modelo', type: 'text' },
    { 
      id: 'provider', 
      label: 'Provider', 
      type: 'select',
      options: [
        { label: 'OpenAI', value: 'openai' },
        { label: 'Anthropic', value: 'anthropic' },
        { label: 'Local (Llama)', value: 'local' }
      ]
    },
    { 
      id: 'is_active', 
      label: 'Estado', 
      type: 'status',
      options: [
        { label: 'Online', value: 'true' },
        { label: 'Offline', value: 'false' }
      ]
    }
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-1">Catálogo de Modelos</h1>
          <p className="text-muted-foreground text-sm md:text-lg">Configuração de LLMs, precificação e roteamento padrão.</p>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl font-bold flex items-center justify-center gap-2 transition-colors shadow-lg shadow-primary/20 w-full sm:w-auto"
        >
          <Plus className="w-5 h-5" />
          Registrar Modelo
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        <div className="bg-card p-4 md:p-6 rounded-2xl border border-border shadow-sm" role="status">
          <h2 className="text-muted-foreground text-[10px] font-black uppercase tracking-widest mb-1 md:mb-2">Total</h2>
          <div className="text-xl md:text-3xl font-black text-foreground">{modelsData?.total || 0}</div>
        </div>
        <div className="bg-card p-4 md:p-6 rounded-2xl border border-border shadow-sm" role="status">
          <h2 className="text-muted-foreground text-[10px] font-black uppercase tracking-widest mb-1 md:mb-2">Ativos</h2>
          <div className="text-xl md:text-3xl font-black text-primary">{modelsData?.items?.filter((m: Model) => m.is_active).length || 0}</div>
        </div>
        <div className="bg-card p-4 md:p-6 rounded-2xl border border-border shadow-sm" role="status">
          <h2 className="text-muted-foreground text-[10px] font-black uppercase tracking-widest mb-1 md:mb-2">Providers</h2>
          <div className="text-xl md:text-3xl font-black text-foreground">{new Set(modelsData?.items?.map((m: Model) => m.provider)).size || 0}</div>
        </div>
        <div className="bg-card p-4 md:p-6 rounded-2xl border border-border shadow-sm" role="status">
          <h2 className="text-muted-foreground text-[10px] font-black uppercase tracking-widest mb-1 md:mb-2">Runtimes</h2>
          <div className="text-xl md:text-3xl font-black text-yellow-500">{runtimes?.filter(r => r.status === 'ready').length || 0}</div>
        </div>
      </div>

      <AdvancedTable
        id="models"
        columns={columns}
        data={modelsData?.items || []}
        rowCount={modelsData?.total || 0}
        isLoading={isLoadingModels}
        pagination={pagination}
        onPaginationChange={setPagination}
        onSortingChange={setSorting}
        onFiltersApply={setFilters}
        filterConfig={filterConfig}
        batchActions={batchActions}
      />

      {isCreateOpen && (
        <div className="fixed inset-0 z-[110] bg-foreground/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-3xl rounded-3xl border border-border bg-card shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between gap-4 border-b border-border px-6 py-4">
              <div>
                <h2 className="text-xl font-black text-foreground">Registrar Modelo</h2>
                <p className="text-sm text-muted-foreground">Cria um registro em `ModelRegistry` usando o backend real.</p>
              </div>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="rounded-xl border border-border px-3 py-2 text-sm font-bold text-muted-foreground hover:text-foreground hover:bg-secondary"
              >
                Fechar
              </button>
            </div>

            <div className="grid gap-4 p-6 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Display Name</span>
                <input
                  value={createForm.display_name}
                  onChange={e => setCreateForm(prev => ({ ...prev, display_name: e.target.value }))}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                  placeholder="Ex: Gemini Flash"
                />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Model ID</span>
                <input
                  value={createForm.model_id}
                  onChange={e => setCreateForm(prev => ({ ...prev, model_id: e.target.value }))}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                  placeholder="Ex: gemini-2.0-flash"
                />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Alias</span>
                <input
                  value={createForm.model_alias}
                  onChange={e => setCreateForm(prev => ({ ...prev, model_alias: e.target.value }))}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                  placeholder="Opcional"
                />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Provider</span>
                <select
                  value={createForm.provider}
                  onChange={e => setCreateForm(prev => ({ ...prev, provider: e.target.value }))}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                >
                  <option value="llama.cpp">llama.cpp</option>
                  <option value="ollama">ollama</option>
                  <option value="vllm">vllm</option>
                  <option value="tgi">tgi</option>
                  <option value="openai_compatible">openai_compatible</option>
                  <option value="openrouter">openrouter</option>
                  <option value="openai">openai</option>
                  <option value="anthropic">anthropic</option>
                  <option value="deepseek">deepseek</option>
                </select>
              </label>
              <label className="space-y-2 md:col-span-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Model File</span>
                <input
                  value={createForm.model_file}
                  onChange={e => setCreateForm(prev => ({ ...prev, model_file: e.target.value }))}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                  placeholder="Ex: models/llama-3.1-8b-instruct.gguf"
                />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Backend</span>
                <select
                  value={createForm.inference_backend_id}
                  onChange={e => setCreateForm(prev => ({ ...prev, inference_backend_id: e.target.value }))}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                >
                  <option value="">Nenhum / criar sem backend</option>
                  {backendOptions.map(backend => (
                    <option key={backend.id} value={backend.id}>
                      {backend.name} · {backend.provider}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Context Length</span>
                <input
                  type="number"
                  min={512}
                  max={131072}
                  value={createForm.context_length}
                  onChange={e => setCreateForm(prev => ({ ...prev, context_length: Number(e.target.value) }))}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Status</span>
                <input
                  value={createForm.status}
                  onChange={e => setCreateForm(prev => ({ ...prev, status: e.target.value }))}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                  placeholder="configured"
                />
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-border bg-secondary/40 px-4 py-3">
                <input
                  type="checkbox"
                  checked={createForm.is_active}
                  onChange={e => setCreateForm(prev => ({ ...prev, is_active: e.target.checked }))}
                />
                <span className="text-sm font-medium text-foreground">Ativo</span>
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-border bg-secondary/40 px-4 py-3">
                <input
                  type="checkbox"
                  checked={createForm.is_default}
                  onChange={e => setCreateForm(prev => ({ ...prev, is_default: e.target.checked }))}
                />
                <span className="text-sm font-medium text-foreground">Definir como padrão</span>
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-border bg-secondary/40 px-4 py-3">
                <input
                  type="checkbox"
                  checked={createForm.allow_reasoning}
                  onChange={e => setCreateForm(prev => ({ ...prev, allow_reasoning: e.target.checked }))}
                />
                <span className="text-sm font-medium text-foreground">Allow reasoning</span>
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-border bg-secondary/40 px-4 py-3">
                <input
                  type="checkbox"
                  checked={createForm.include_reasoning_default}
                  onChange={e => setCreateForm(prev => ({ ...prev, include_reasoning_default: e.target.checked }))}
                />
                <span className="text-sm font-medium text-foreground">Include reasoning default</span>
              </label>
              <label className="space-y-2 md:col-span-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Prompt Template</span>
                <textarea
                  value={createForm.prompt_template}
                  onChange={e => setCreateForm(prev => ({ ...prev, prompt_template: e.target.value }))}
                  className="min-h-[120px] w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                  placeholder="Opcional"
                />
              </label>
            </div>

            <div className="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
              <button
                onClick={() => setIsCreateOpen(false)}
                className="rounded-2xl border border-border px-4 py-2.5 text-sm font-bold text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                Cancelar
              </button>
              <button
                onClick={() => createModelMutation.mutate()}
                disabled={createModelMutation.isPending || !createForm.model_id.trim() || !createForm.model_file.trim()}
                className="rounded-2xl bg-primary px-5 py-2.5 text-sm font-bold text-white hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {createModelMutation.isPending ? 'Registrando...' : 'Registrar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
