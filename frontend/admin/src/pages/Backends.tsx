import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import { Cpu, Server, Activity, Plus, CheckCircle2, AlertCircle, Terminal, Info, Trash2, ShieldCheck, ShieldAlert } from 'lucide-react'
import { useState } from 'react'
import { AdvancedTable } from '../components/table/advanced-table'
import { toast } from 'sonner'
import type { ColumnDef } from '@tanstack/react-table'

interface Backend {
  id: string
  name: string
  base_url: string
  is_enabled: boolean
  is_active: boolean
  provider_type: string
  max_concurrency: number
}

export default function Backends() {
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 10 })
  const [filters, setFilters] = useState<any>({})
  const [sorting, setSorting] = useState<any[]>([])

  const { data, isLoading } = useQuery({
    queryKey: ['backends', pagination, filters, sorting],
    queryFn: async () => {
      const res = await api.get('/admin/backends', {
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

  const columns: ColumnDef<Backend>[] = [
    {
      accessorKey: 'name',
      header: 'Backend / Provider',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${row.original.is_enabled ? 'bg-primary/10 text-primary' : 'bg-secondary text-muted-foreground'}`}>
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-foreground">{row.original.name}</h3>
            <div className="text-[10px] font-mono text-muted-foreground">{row.original.id}</div>
          </div>
        </div>
      )
    },
    {
      accessorKey: 'base_url',
      header: 'Endpoint',
      cell: ({ row }) => (
        <div className="flex items-center gap-2 text-[10px] font-mono text-muted-foreground max-w-[200px] truncate">
          <Terminal className="w-3 h-3 shrink-0" />
          {row.original.base_url}
        </div>
      )
    },
    {
      accessorKey: 'provider_type',
      header: 'Tipo',
      cell: ({ row }) => (
        <span className="px-2 py-0.5 bg-secondary text-muted-foreground text-[10px] font-black rounded-md uppercase">
          {row.original.provider_type}
        </span>
      )
    },
    {
      accessorKey: 'is_enabled',
      header: 'Status',
      cell: ({ row }) => row.original.is_enabled ? (
        <span className="inline-flex items-center gap-1.5 text-primary text-[10px] font-black uppercase tracking-wider">
          <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" /> ONLINE
        </span>
      ) : (
        <span className="inline-flex items-center gap-1.5 text-muted-foreground text-[10px] font-black uppercase tracking-wider">
          <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground" /> OFFLINE
        </span>
      )
    },
    {
      accessorKey: 'max_concurrency',
      header: 'Concurrency',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <div className="w-12 h-1.5 bg-secondary rounded-full overflow-hidden">
            <div className="h-full bg-primary" style={{ width: '45%' }} />
          </div>
          <span className="text-[10px] font-bold">{row.original.max_concurrency}</span>
        </div>
      )
    },
    {
      id: 'actions',
      header: 'Ações',
      cell: ({ row }) => (
        <div className="flex gap-2 justify-end">
          <button className="p-2 hover:bg-secondary rounded-lg text-muted-foreground transition-all">
            <Activity className="w-4 h-4" />
          </button>
          <button className="p-2 hover:bg-secondary rounded-lg text-muted-foreground transition-all">
            <Info className="w-4 h-4" />
          </button>
        </div>
      ),
      enableHiding: false,
    }
  ]

  const batchActions = [
    {
      label: 'Testar Conexão',
      icon: <RefreshCw size={14} />,
      onClick: (rows: Backend[]) => toast.success(`Teste iniciado para ${rows.length} backends`),
    },
    {
      label: 'Suspender Tráfego',
      icon: <ShieldAlert size={14} />,
      onClick: (rows: Backend[]) => toast.error('Operação crítica: requer autorização nível 3.'),
      variant: 'destructive' as const
    }
  ]

  const filterConfig = [
    { id: 'name', label: 'Nome do Backend', type: 'text' },
    { 
      id: 'provider_type', 
      label: 'Tipo de Provider', 
      type: 'select',
      options: [
        { label: 'LLM Server', value: 'llm_server' },
        { label: 'External API', value: 'external_api' },
        { label: 'Serverless', value: 'serverless' }
      ]
    },
    { 
      id: 'is_enabled', 
      label: 'Status', 
      type: 'status',
      options: [
        { label: 'Online', value: 'true' },
        { label: 'Offline', value: 'false' }
      ]
    }
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-foreground mb-2">Backends / Providers</h1>
          <p className="text-muted-foreground">Gestão de clusters de inferência, providers externos e saúde do runtime.</p>
        </div>
        <div className="flex gap-3">
          <button className="bg-secondary hover:bg-secondary/80 text-foreground px-4 py-2 rounded-xl font-bold transition-colors">
            Testar Conexões
          </button>
          <button className="bg-primary hover:bg-primary/90 text-white px-4 py-2 rounded-xl font-bold flex items-center gap-2 transition-colors shadow-lg shadow-primary/20">
            <Plus className="w-5 h-5" />
            Adicionar Backend
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-card p-6 rounded-2xl border border-border shadow-sm flex items-center gap-4">
          <div className="p-3 bg-primary/10 text-primary rounded-xl"><Server className="w-6 h-6" /></div>
          <div>
            <div className="text-muted-foreground text-xs font-bold uppercase tracking-wider">Backends Ativos</div>
            <div className="text-2xl font-black text-foreground">{data?.items?.filter((b: Backend) => b.is_enabled).length || 0} / {data?.total || 0}</div>
          </div>
        </div>
        <div className="bg-card p-6 rounded-2xl border border-border shadow-sm flex items-center gap-4">
          <div className="p-3 bg-accent/10 text-accent rounded-xl"><Activity className="w-6 h-6" /></div>
          <div>
            <div className="text-muted-foreground text-xs font-bold uppercase tracking-wider">Requisições Ativas</div>
            <div className="text-2xl font-black text-foreground">142</div>
          </div>
        </div>
        <div className="bg-card p-6 rounded-2xl border border-border shadow-sm flex items-center gap-4">
          <div className="p-3 bg-primary/10 text-primary rounded-xl"><CheckCircle2 className="w-6 h-6" /></div>
          <div>
            <div className="text-muted-foreground text-xs font-bold uppercase tracking-wider">Uptime Global</div>
            <div className="text-2xl font-black text-foreground">99.98%</div>
          </div>
        </div>
      </div>

      <AdvancedTable
        id="backends"
        columns={columns}
        data={data?.items || []}
        rowCount={data?.total || 0}
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

import { RefreshCw } from 'lucide-react'
