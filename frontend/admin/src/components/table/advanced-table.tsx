import * as React from "react"
import type { ColumnDef, ColumnFiltersState, PaginationState, SortingState, VisibilityState } from "@tanstack/react-table"
import {
  flexRender,
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { 
  ChevronDown, 
  ChevronUp, 
  ChevronsUpDown, 
  Maximize2, 
  Minimize2, 
  Download,
  Filter,
  FileJson,
  FileSpreadsheet
} from "lucide-react"
import { cn } from "../../lib/utils"
import { TablePagination } from "./table-pagination"
import { ColumnToggle } from "./column-toggle"
import { FilterModal } from "./filter-modal"
import { toast } from "sonner"

interface AdvancedTableProps<TData, TValue> {
  id: string // For persistence
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  rowCount?: number
  isLoading?: boolean
  pagination?: {
    pageIndex: number
    pageSize: number
  }
  onPaginationChange?: (pagination: { pageIndex: number, pageSize: number }) => void
  onSortingChange?: (sorting: SortingState) => void
  onFiltersApply?: (filters: any) => void
  filterConfig?: any[]
  batchActions?: {
    label: string
    icon: React.ReactNode
    onClick: (rows: TData[]) => void
    variant?: 'default' | 'destructive'
  }[]
}

export function AdvancedTable<TData, TValue>({
  id,
  columns,
  data,
  rowCount,
  isLoading,
  pagination,
  onPaginationChange,
  onSortingChange,
  onFiltersApply,
  filterConfig = [],
  batchActions = []
}: AdvancedTableProps<TData, TValue>) {
  const [rowSelection, setRowSelection] = React.useState({})
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>(() => {
    const saved = localStorage.getItem(`table-cols-${id}`)
    return saved ? JSON.parse(saved) : {}
  })
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [internalPagination, setInternalPagination] = React.useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [isFullscreen, setIsFullscreen] = React.useState(false)
  const [isFilterOpen, setIsFilterOpen] = React.useState(false)
  const tablePagination = pagination ?? internalPagination

  // Selection column
  const tableColumns = React.useMemo(() => [
    {
      id: "select",
      header: ({ table }: any) => (
        <input
          type="checkbox"
          className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
          checked={table.getIsAllPageRowsSelected()}
          onChange={(e) => table.toggleAllPageRowsSelected(!!e.target.checked)}
          aria-label="Selecionar todos"
        />
      ),
      cell: ({ row }: any) => (
        <input
          type="checkbox"
          className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
          checked={row.getIsSelected()}
          onChange={(e) => row.toggleSelected(!!e.target.checked)}
          aria-label="Selecionar linha"
        />
      ),
      enableSorting: false,
      enableHiding: false,
    },
    ...columns
  ], [columns])

  const table = useReactTable({
    data,
    columns: tableColumns,
    state: {
      sorting,
      columnVisibility,
      rowSelection,
      pagination: tablePagination,
    },
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    onPaginationChange: (updater) => {
      const next = typeof updater === 'function' ? updater(tablePagination) : updater
      if (!pagination) {
        setInternalPagination(next)
      }
      onPaginationChange?.(next)
    },
    onSortingChange: (updater) => {
      const next = typeof updater === 'function' ? updater(sorting) : updater
      setSorting(next)
      onSortingChange?.(next)
    },
    onColumnVisibilityChange: (updater) => {
      const next = typeof updater === 'function' ? updater(columnVisibility) : updater
      setColumnVisibility(next)
      localStorage.setItem(`table-cols-${id}`, JSON.stringify(next))
    },
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
    manualPagination: true,
    manualSorting: true,
    pageCount: rowCount ? Math.ceil(rowCount / tablePagination.pageSize) : Math.ceil(data.length / tablePagination.pageSize),
  })

  const selectedRows = table.getSelectedRowModel().rows.map(r => r.original)

  const exportData = (format: 'csv' | 'json') => {
    const dataToExport = table.getCoreRowModel().rows.map(r => r.original)
    if (format === 'json') {
      const blob = new Blob([JSON.stringify(dataToExport, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${id}-${new Date().toISOString()}.json`
      a.click()
    } else {
      const headers = table.getAllColumns().filter(c => c.getIsVisible() && c.id !== 'select').map(c => c.id)
      const csv = [
        headers.join(','),
        ...dataToExport.map(row => headers.map(h => {
          const val = (row as any)[h]
          return typeof val === 'object' ? JSON.stringify(val) : `"${val}"`
        }).join(','))
      ].join('\n')
      const blob = new Blob([csv], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${id}-${new Date().toISOString()}.csv`
      a.click()
    }
    toast.success(`Exportado para ${format.toUpperCase()} com sucesso!`)
  }

  return (
    <div className={cn(
      "space-y-4",
      isFullscreen && "fixed inset-0 z-[100] bg-background p-8 overflow-auto"
    )}>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 min-h-[40px]">
          {selectedRows.length > 0 && (
            <div className="flex items-center gap-2 animate-in fade-in slide-in-from-left-2">
              <span className="text-sm font-bold text-primary px-3 py-1 bg-primary/10 rounded-full border border-primary/20">
                {selectedRows.length} selecionados
              </span>
              <div className="h-4 w-[1px] bg-border mx-1" />
              {batchActions.map((action, i) => (
                <button
                  key={i}
                  onClick={() => action.onClick(selectedRows)}
                  className={cn(
                    "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all",
                    action.variant === 'destructive' 
                      ? "text-destructive hover:bg-destructive/10" 
                      : "text-foreground hover:bg-secondary"
                  )}
                >
                  {action.icon}
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center bg-card border border-border rounded-xl p-1 shadow-sm">
            <button 
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-2 hover:bg-secondary rounded-lg text-muted-foreground transition-all"
              title={isFullscreen ? "Sair da tela cheia" : "Modo tela cheia"}
            >
              {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
            </button>
            <div className="w-[1px] h-4 bg-border mx-1" />
            <div className="relative group">
              <button className="p-2 hover:bg-secondary rounded-lg text-muted-foreground transition-all">
                <Download size={18} />
              </button>
              <div className="absolute right-0 top-full mt-2 hidden group-hover:block w-40 bg-card border border-border rounded-xl shadow-xl z-[120] overflow-hidden">
                <button 
                  onClick={() => exportData('csv')}
                  className="w-full flex items-center gap-2 px-4 py-2 text-xs font-bold hover:bg-secondary transition-colors text-left"
                >
                  <FileSpreadsheet size={14} /> Exportar CSV
                </button>
                <button 
                  onClick={() => exportData('json')}
                  className="w-full flex items-center gap-2 px-4 py-2 text-xs font-bold hover:bg-secondary border-t border-border transition-colors text-left"
                >
                  <FileJson size={14} /> Exportar JSON
                </button>
              </div>
            </div>
            <div className="w-[1px] h-4 bg-border mx-1" />
            <ColumnToggle table={table} />
          </div>
          <button 
            onClick={() => setIsFilterOpen(true)}
            className="bg-primary text-white px-4 py-2 rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-primary/20 hover:bg-primary/90 transition-all"
          >
            <Filter size={18} />
            Filtros
          </button>
        </div>
      </div>

      <FilterModal 
        isOpen={isFilterOpen}
        onClose={() => setIsFilterOpen(false)}
        filterConfig={filterConfig}
        onReset={() => onFiltersApply?.({})}
        onApply={(f) => {
          onFiltersApply?.(f)
          setIsFilterOpen(false)
        }}
      />

      <div className="bg-card border border-border rounded-2xl shadow-sm overflow-hidden relative min-h-[200px]">
        {isLoading && (
          <div className="absolute inset-0 bg-background/50 backdrop-blur-[1px] z-10 flex items-center justify-center">
            <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id} className="border-b border-border bg-secondary/30">
                  {headerGroup.headers.map((header) => (
                    <th key={header.id} className="px-6 py-4">
                      {header.isPlaceholder ? null : (
                        <div
                          className={cn(
                            "flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-muted-foreground",
                            header.column.getCanSort() && "cursor-pointer select-none hover:text-foreground transition-colors"
                          )}
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                          {header.column.getCanSort() && (
                            <div className="flex flex-col">
                              {{
                                asc: <ChevronUp size={12} className="text-primary" />,
                                desc: <ChevronDown size={12} className="text-primary" />,
                              }[header.column.getIsSorted() as string] ?? <ChevronsUpDown size={12} className="opacity-30" />}
                            </div>
                          )}
                        </div>
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-border">
              {table.getRowModel().rows?.length ? (
                table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    data-state={row.getIsSelected() && "selected"}
                    className={cn(
                      "hover:bg-secondary/20 transition-colors group",
                      row.getIsSelected() && "bg-primary/5"
                    )}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-6 py-4">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={tableColumns.length} className="h-40 text-center text-muted-foreground">
                    <div className="flex flex-col items-center gap-2">
                      <div className="p-3 bg-secondary rounded-full">
                        <Filter className="w-6 h-6 opacity-20" />
                      </div>
                      <p className="font-medium">Nenhum resultado encontrado.</p>
                      <button 
                        onClick={() => onFiltersApply?.({})}
                        className="text-xs text-primary font-bold hover:underline"
                      >
                        Limpar todos os filtros
                      </button>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <TablePagination table={table} />
    </div>
  )
}
