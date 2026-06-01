import { useQuery } from '@tanstack/react-query'
import { useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { Plus, ShieldCheck, ShieldAlert, Edit, Ban, Trash2, Download } from 'lucide-react'
import { useState, useMemo, useCallback } from 'react'
import { AdvancedTable } from '../components/table/advanced-table'
import { toast } from 'sonner'
import type { ColumnDef } from '@tanstack/react-table'

interface Client {
  id: string
  name: string
  billing_plan_id: string
  billing_status: string
  is_blocked: boolean
  rate_limit_per_minute: number
  daily_token_quota: number
  created_at: string
}

export default function Clients() {
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 25 })
  const [filters, setFilters] = useState<any>({})
  const [sorting, setSorting] = useState<any[]>([])

  const { data, isLoading } = useQuery({
    queryKey: ['clients', pagination, filters, sorting],
    queryFn: async () => {
      const res = await api.get('/admin/clients', {
        params: {
          page: pagination.pageIndex + 1,
          limit: pagination.pageSize,
          ...filters,
          sort: sorting.map(s => `${s.id}:${s.desc ? 'desc' : 'asc'}`).join(',')
        }
      })
      // If API doesn't support pagination yet, it returns array. Handle both.
      if (Array.isArray(res.data)) {
        return { items: res.data, total: res.data.length }
      }
      return res.data // Expected: { items: [], total: 0 }
    }
  })

  const columns = useMemo<ColumnDef<Client>[]>(() => [
    {
      accessorKey: 'name',
      header: 'Cliente',
      cell: ({ row }) => (
        <div>
          <div className="font-bold text-foreground">{row.original.name}</div>
          <div className="text-[10px] font-mono text-muted-foreground">{row.original.id}</div>
        </div>
      )
    },
    {
      accessorKey: 'billing_plan_id',
      header: 'Plano / Billing',
      cell: ({ row }) => (
        <div>
          <div className="text-sm font-medium">{row.original.billing_plan_id || 'Plano Padrão'}</div>
          <div className="text-[10px] text-muted-foreground uppercase font-black">{row.original.billing_status}</div>
        </div>
      )
    },
    {
      accessorKey: 'is_blocked',
      header: 'Status',
      cell: ({ row }) => row.original.is_blocked ? (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-destructive/10 text-destructive text-[10px] font-black rounded-md">
          <ShieldAlert className="w-3 h-3" /> BLOQUEADO
        </span>
      ) : (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-500/10 text-emerald-600 text-[10px] font-black rounded-md">
          <ShieldCheck className="w-3 h-3" /> ATIVO
        </span>
      )
    },
    {
      accessorKey: 'rate_limit_per_minute',
      header: 'Quotas',
      cell: ({ row }) => (
        <div>
          <div className="text-foreground font-bold text-sm">{row.original.rate_limit_per_minute.toLocaleString()} RPM</div>
          <div className="text-muted-foreground text-[10px]">{row.original.daily_token_quota.toLocaleString()} tokens/dia</div>
        </div>
      )
    },
    {
      id: 'actions',
      header: 'Ações',
      cell: ({ row }) => (
        <div className="flex gap-2 justify-end">
          <button className="p-2 hover:bg-secondary rounded-lg text-muted-foreground transition-all">
            <Edit className="w-4 h-4" />
          </button>
          <button className="p-2 hover:bg-destructive/10 rounded-lg text-destructive transition-all">
            <Ban className="w-4 h-4" />
          </button>
        </div>
      ),
      enableHiding: false,
    }
  ], [])

  const handleExport = useCallback((rows: Client[]) => {
    const blob = new Blob([JSON.stringify(rows, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `clients-selection-${new Date().getTime()}.json`
    a.click()
    toast.success(`${rows.length} registros exportados!`)
  }, [])

  const handleDelete = useCallback(async (rows: Client[]) => {
    if (rows.length === 0) return

    if (rows.length > 1) {
      toast.error('Ação de exclusão em massa requer confirmação extra.')
      return
    }

    const client = rows[0]
    const confirmed = window.confirm(`Excluir o cliente "${client.name}"?`)
    if (!confirmed) return

    try {
      await api.deleteClient(client.id)
      await queryClient.invalidateQueries({ queryKey: ['clients'] })
      toast.success('Cliente excluído com sucesso')
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Falha ao excluir cliente'
      toast.error(detail)
    }
  }, [queryClient])

  const batchActions = useMemo(() => [
    {
      label: 'Bloquear',
      icon: <Ban size={14} />,
      onClick: (rows: Client[]) => {
        toast.promise(Promise.resolve(), {
          loading: 'Bloqueando clientes...',
          success: `${rows.length} clientes bloqueados com sucesso!`,
          error: 'Falha ao bloquear clientes'
        })
      },
      variant: 'destructive' as const
    },
    {
      label: 'Excluir',
      icon: <Trash2 size={14} />,
      onClick: handleDelete,
      variant: 'destructive' as const
    },
    {
      label: 'Exportar Selecionados',
      icon: <Download size={14} />,
      onClick: handleExport
    }
  ], [handleDelete, handleExport])

  const filterConfig = useMemo(() => [
    { id: 'name', label: 'Nome do Cliente', type: 'text' },
    { 
      id: 'billing_status', 
      label: 'Status de Faturamento', 
      type: 'status',
      options: [
        { label: 'Pago', value: 'paid' },
        { label: 'Pendente', value: 'pending' },
        { label: 'Atrasado', value: 'overdue' }
      ]
    },
    {
      id: 'billing_plan_id',
      label: 'Plano',
      type: 'select',
      options: [
        { label: 'Enterprise', value: 'enterprise' },
        { label: 'Business', value: 'business' },
        { label: 'Developer', value: 'developer' }
      ]
    },
    { id: 'created_at', label: 'Data de Cadastro', type: 'date-range' }
  ], [])

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-1">Gestão de Clientes</h1>
          <p className="text-muted-foreground text-sm md:text-lg">Controle de acesso, quotas e faturamento por tenant.</p>
        </div>
        <button className="bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl font-bold flex items-center justify-center gap-2 transition-colors shadow-lg shadow-primary/20 w-full sm:w-auto">
          <Plus className="w-5 h-5" />
          Novo Cliente
        </button>
      </div>

      <AdvancedTable
        id="clients"
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
