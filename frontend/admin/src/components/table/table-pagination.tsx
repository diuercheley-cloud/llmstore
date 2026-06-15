import type { Table } from "@tanstack/react-table"
import { 
  ChevronLeft, 
  ChevronRight, 
  ChevronsLeft, 
  ChevronsRight 
} from "lucide-react"
import { cn } from "../../lib/utils"

interface TablePaginationProps<TData> {
  table: Table<TData>
}

export function TablePagination<TData>({
  table
}: TablePaginationProps<TData>) {
  return (
    <div className="flex items-center justify-between px-2">
      <div className="flex-1 text-sm text-muted-foreground">
        {table.getFilteredSelectedRowModel().rows.length} de{" "}
        {table.getFilteredRowModel().rows.length} linha(s) selecionada(s).
      </div>
      <div className="flex items-center space-x-6 lg:space-x-8">
        <div className="flex items-center space-x-2">
          <p className="text-sm font-bold">Linhas por página</p>
          <select
            value={table.getState().pagination.pageSize}
            onChange={(e) => {
              const size = Number(e.target.value)
              table.setPageSize(size)
            }}
            className="h-8 w-[70px] bg-card border border-border rounded-lg text-xs font-bold focus:ring-2 focus:ring-primary outline-none transition-all"
          >
            {[10, 25, 50, 100].map((pageSize) => (
              <option key={pageSize} value={pageSize}>
                {pageSize}
              </option>
            ))}
          </select>
        </div>
        <div className="flex w-[100px] items-center justify-center text-sm font-bold">
          Página {table.getState().pagination.pageIndex + 1} de{" "}
          {table.getPageCount()}
        </div>
        <div className="flex items-center space-x-2">
          <button
            className="hidden h-8 w-8 p-0 lg:flex items-center justify-center border border-border rounded-lg hover:bg-secondary disabled:opacity-50 transition-all"
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
          >
            <span className="sr-only">Primeira página</span>
            <ChevronsLeft size={16} />
          </button>
          <button
            className="h-8 w-8 p-0 flex items-center justify-center border border-border rounded-lg hover:bg-secondary disabled:opacity-50 transition-all"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            <span className="sr-only">Página anterior</span>
            <ChevronLeft size={16} />
          </button>
          <button
            className="h-8 w-8 p-0 flex items-center justify-center border border-border rounded-lg hover:bg-secondary disabled:opacity-50 transition-all"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            <span className="sr-only">Próxima página</span>
            <ChevronRight size={16} />
          </button>
          <button
            className="hidden h-8 w-8 p-0 lg:flex items-center justify-center border border-border rounded-lg hover:bg-secondary disabled:opacity-50 transition-all"
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
          >
            <span className="sr-only">Última página</span>
            <ChevronsRight size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
