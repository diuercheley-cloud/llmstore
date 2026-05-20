import type { Table } from "@tanstack/react-table"
import { Settings2, Eye, EyeOff } from "lucide-react"
import { cn } from "../../lib/utils"

interface ColumnToggleProps<TData> {
  table: Table<TData>
}

export function ColumnToggle<TData>({
  table,
}: ColumnToggleProps<TData>) {
  return (
    <div className="relative group">
      <button 
        className="p-2 hover:bg-secondary rounded-lg text-muted-foreground transition-all flex items-center gap-2"
        title="Personalizar colunas"
      >
        <Settings2 size={18} />
      </button>
      <div className="absolute right-0 top-full mt-2 hidden group-hover:block w-56 bg-card border border-border rounded-xl shadow-xl z-20 overflow-hidden py-2 animate-in fade-in slide-in-from-top-2">
        <div className="px-4 py-2 border-b border-border mb-2">
          <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Colunas Visíveis</span>
        </div>
        <div className="max-h-[300px] overflow-y-auto px-2">
          {table
            .getAllColumns()
            .filter(
              (column) =>
                typeof column.accessorFn !== "undefined" && column.getCanHide()
            )
            .map((column) => {
              const isVisible = column.getIsVisible()
              return (
                <button
                  key={column.id}
                  onClick={() => column.toggleVisibility(!isVisible)}
                  className={cn(
                    "w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-bold transition-colors mb-1",
                    isVisible ? "bg-primary/5 text-primary" : "hover:bg-secondary text-muted-foreground"
                  )}
                >
                  <span className="capitalize">{column.id.replace(/_/g, ' ')}</span>
                  {isVisible ? <Eye size={14} /> : <EyeOff size={14} />}
                </button>
              )
            })}
        </div>
      </div>
    </div>
  )
}
