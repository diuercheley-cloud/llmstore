import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { AdvancedTable } from '../components/table/advanced-table'
import { toast } from 'sonner'
import type { ColumnDef } from '@tanstack/react-table'
import {
  Package,
  Trash2,
  ToggleLeft,
  ToggleRight,
  RefreshCw,
  Shield,
  Upload,
  ExternalLink,
} from 'lucide-react'

type PluginInstall = {
  id: string
  plugin_entry_id: string
  current_version_id: string
  install_path: string
  status: string
  is_enabled: boolean
  config_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

type MarketplaceEntry = {
  id: string
  name: string
  description: string
  author: string
  license: string
  plugin_type: string
  official: boolean
  avg_rating: number
  created_at: string
  updated_at: string
}

export default function Plugins() {
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 10 })
  const [filters, setFilters] = useState<any>({})
  const [sorting, setSorting] = useState<any[]>([])
  const [uploading, setUploading] = useState(false)
  const queryClient = useQueryClient()

  const { data: marketplace } = useQuery<MarketplaceEntry[]>({
    queryKey: ['marketplace'],
    queryFn: () => api.get('/admin/plugins/marketplace').then((r) => r.data),
  })

  const { data: installs, isLoading } = useQuery<PluginInstall[]>({
    queryKey: ['installs', pagination, filters, sorting],
    queryFn: () => api.get('/admin/plugins/installs').then((r) => r.data),
  })

  const entryMap = new Map<string, MarketplaceEntry>()
  if (marketplace) {
    for (const e of marketplace) entryMap.set(e.id, e)
  }

  const enableMutation = useMutation({
    mutationFn: (id: string) => api.post(`/admin/plugins/${id}/enable`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['installs'] })
      toast.success("Plugin habilitado!")
    }
  })

  const disableMutation = useMutation({
    mutationFn: (id: string) => api.post(`/admin/plugins/${id}/disable`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['installs'] })
      toast.success("Plugin desabilitado!")
    }
  })

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      await api.post('/admin/plugins/install', form)
      queryClient.invalidateQueries({ queryKey: ['installs'] })
      toast.success("Plugin instalado com sucesso!")
    } catch (err) {
      toast.error("Erro ao instalar plugin")
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const columns: ColumnDef<PluginInstall>[] = [
    {
      id: 'plugin',
      header: 'Plugin',
      cell: ({ row }) => {
        const entry = entryMap.get(row.original.plugin_entry_id)
        return (
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${row.original.is_enabled ? 'bg-primary/10 text-primary' : 'bg-secondary text-muted-foreground'}`}>
              <Package className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-foreground">{entry?.name ?? row.original.id.slice(0, 8)}</h3>
              <p className="text-[10px] text-muted-foreground truncate max-w-[200px]">{entry?.description}</p>
            </div>
          </div>
        )
      }
    },
    {
      id: 'author',
      header: 'Autor',
      cell: ({ row }) => {
        const entry = entryMap.get(row.original.plugin_entry_id)
        return <span className="text-[10px] font-bold text-muted-foreground">{entry?.author || 'Unknown'}</span>
      }
    },
    {
      accessorKey: 'is_enabled',
      header: 'Estado',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${row.original.is_enabled ? 'bg-primary animate-pulse' : 'bg-secondary'}`} />
          <span className={`text-[10px] font-black uppercase ${row.original.is_enabled ? 'text-primary' : 'text-muted-foreground'}`}>
            {row.original.is_enabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>
      )
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <span className="px-2 py-0.5 bg-secondary text-muted-foreground text-[10px] font-black rounded-md uppercase">
          {row.original.status}
        </span>
      )
    },
    {
      id: 'actions',
      header: 'Ações',
      cell: ({ row }) => (
        <div className="flex gap-2 justify-end">
          <button 
            onClick={() => row.original.is_enabled ? disableMutation.mutate(row.original.id) : enableMutation.mutate(row.original.id)}
            className="p-2 hover:bg-secondary rounded-lg text-muted-foreground transition-all"
          >
            {row.original.is_enabled ? <ToggleRight className="w-5 h-5" /> : <ToggleLeft className="w-5 h-5" />}
          </button>
          <button className="p-2 hover:bg-secondary rounded-lg text-muted-foreground transition-all">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ),
      enableHiding: false,
    }
  ]

  const batchActions = [
    {
      label: 'Desabilitar Selecionados',
      icon: <ToggleLeft size={14} />,
      onClick: (rows: PluginInstall[]) => toast.success(`${rows.length} plugins desabilitados`),
      variant: 'destructive' as const
    },
    {
      label: 'Desinstalar Selecionados',
      icon: <Trash2 size={14} />,
      onClick: (rows: PluginInstall[]) => toast.error('Ação protegida por MFA.'),
      variant: 'destructive' as const
    }
  ]

  const filterConfig = [
    { id: 'status', label: 'Status do Plugin', type: 'select', options: [
      { label: 'Installed', value: 'installed' },
      { label: 'Error', value: 'error' },
      { label: 'Updating', value: 'updating' }
    ]},
    { id: 'is_enabled', label: 'Estado', type: 'status', options: [
      { label: 'Enabled', value: 'true' },
      { label: 'Disabled', value: 'false' }
    ]}
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-foreground">Plugins</h1>
          <p className="text-muted-foreground mt-1 text-sm">Gerencie extensões e integrações do ecossistema.</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 px-4 py-2.5 bg-primary text-white rounded-xl font-bold text-sm hover:bg-primary/90 cursor-pointer transition-colors shadow-lg shadow-primary/20">
            <Upload className="w-4 h-4" />
            {uploading ? 'Installing...' : 'Install Plugin'}
            <input type="file" accept=".zip,.tar,.tar.gz,.tgz" onChange={handleUpload} className="hidden" disabled={uploading} />
          </label>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['installs'] })}
            className="p-2.5 rounded-xl border border-border bg-card hover:bg-secondary transition-colors shadow-sm"
          >
            <RefreshCw className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
      </div>

      <AdvancedTable
        id="plugins"
        columns={columns}
        data={installs || []}
        rowCount={installs?.length || 0}
        isLoading={isLoading}
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
