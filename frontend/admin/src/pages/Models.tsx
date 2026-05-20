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
  name: string
  provider: string
  is_enabled: boolean
  is_active: boolean
  is_default: boolean
  context_length: number
  pricing_unit: string
  input_price: number
  output_price: number
  model_id: string
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
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 10 })
  const [filters, setFilters] = useState<any>({})
  const [sorting, setSorting] = useState<any[]>([])
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
            <div className="text-[10px] font-mono text-muted-foreground">{row.original.name}</div>
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
      accessorKey: 'is_enabled',
      header: 'Estado',
      cell: ({ row }) => row.original.is_enabled ? (
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
            onClick={() => toggleMutation.mutate({ id: row.original.id, enabled: row.original.is_enabled })}
            className="p-2 hover:bg-secondary rounded-lg text-muted-foreground transition-all"
          >
            {row.original.is_enabled ? <PowerOff className="w-4 h-4" /> : <Power className="w-4 h-4 text-primary" />}
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
      id: 'is_enabled', 
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
        <button className="bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl font-bold flex items-center justify-center gap-2 transition-colors shadow-lg shadow-primary/20 w-full sm:w-auto">
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
          <div className="text-xl md:text-3xl font-black text-primary">{modelsData?.items?.filter(m => m.is_enabled).length || 0}</div>
        </div>
        <div className="bg-card p-4 md:p-6 rounded-2xl border border-border shadow-sm" role="status">
          <h2 className="text-muted-foreground text-[10px] font-black uppercase tracking-widest mb-1 md:mb-2">Providers</h2>
          <div className="text-xl md:text-3xl font-black text-foreground">{new Set(modelsData?.items?.map(m => m.provider)).size || 0}</div>
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
    </div>
  )
}
