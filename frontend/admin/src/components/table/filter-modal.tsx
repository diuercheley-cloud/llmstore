import * as React from "react"
import { X, Calendar as CalendarIcon, Search } from "lucide-react"
import { cn } from "../../lib/utils"

interface FilterModalProps {
  isOpen: boolean
  onClose: () => void
  onApply: (filters: any) => void
  onReset: () => void
  filterConfig: {
    id: string
    label: string
    type: 'text' | 'select' | 'date-range' | 'status'
    options?: { label: string, value: string }[]
  }[]
}

export function FilterModal({
  isOpen,
  onClose,
  onApply,
  onReset,
  filterConfig
}: FilterModalProps) {
  const [filters, setFilters] = React.useState<Record<string, any>>({})

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-card w-full max-w-lg rounded-3xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between p-6 border-b border-border bg-secondary/30">
          <div>
            <h2 className="text-xl font-bold">Filtros Avançados</h2>
            <p className="text-xs text-muted-foreground mt-1">Refine sua busca com múltiplos critérios.</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-secondary rounded-xl text-muted-foreground transition-all">
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
          {filterConfig.map((config) => (
            <div key={config.id} className="space-y-2">
              <label className="text-xs font-black uppercase tracking-widest text-muted-foreground">
                {config.label}
              </label>
              
              {config.type === 'text' && (
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input
                    type="text"
                    className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-xl focus:ring-2 focus:ring-primary outline-none transition-all"
                    placeholder={`Filtrar por ${config.label.toLowerCase()}...`}
                    value={filters[config.id] || ''}
                    onChange={(e) => setFilters({ ...filters, [config.id]: e.target.value })}
                  />
                </div>
              )}

              {config.type === 'select' && (
                <select
                  className="w-full px-4 py-2 bg-background border border-border rounded-xl focus:ring-2 focus:ring-primary outline-none transition-all"
                  value={filters[config.id] || ''}
                  onChange={(e) => setFilters({ ...filters, [config.id]: e.target.value })}
                >
                  <option value="">Todos</option>
                  {config.options?.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              )}

              {config.type === 'date-range' && (
                <div className="grid grid-cols-2 gap-2">
                  <div className="relative">
                    <CalendarIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                      type="date"
                      className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-xl focus:ring-2 focus:ring-primary outline-none transition-all text-sm"
                      value={filters[`${config.id}_start`] || ''}
                      onChange={(e) => setFilters({ ...filters, [`${config.id}_start`]: e.target.value })}
                    />
                  </div>
                  <div className="relative">
                    <CalendarIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                      type="date"
                      className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-xl focus:ring-2 focus:ring-primary outline-none transition-all text-sm"
                      value={filters[`${config.id}_end`] || ''}
                      onChange={(e) => setFilters({ ...filters, [`${config.id}_end`]: e.target.value })}
                    />
                  </div>
                </div>
              )}

              {config.type === 'status' && (
                <div className="flex flex-wrap gap-2">
                  {config.options?.map(opt => {
                    const isActive = filters[config.id] === opt.value
                    return (
                      <button
                        key={opt.value}
                        onClick={() => setFilters({ ...filters, [config.id]: isActive ? null : opt.value })}
                        className={cn(
                          "px-3 py-1.5 rounded-full text-xs font-bold border transition-all",
                          isActive 
                            ? "bg-primary border-primary text-white shadow-lg shadow-primary/20" 
                            : "bg-secondary border-border text-muted-foreground hover:border-primary/50"
                        )}
                      >
                        {opt.label}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="p-6 border-t border-border bg-secondary/30 flex gap-3">
          <button
            onClick={() => {
              setFilters({})
              onReset()
            }}
            className="flex-1 px-4 py-2.5 bg-secondary text-foreground rounded-xl font-bold hover:bg-secondary/80 transition-all"
          >
            Limpar
          </button>
          <button
            onClick={() => onApply(filters)}
            className="flex-2 px-8 py-2.5 bg-primary text-white rounded-xl font-bold shadow-lg shadow-primary/20 hover:bg-primary/90 transition-all"
          >
            Aplicar Filtros
          </button>
        </div>
      </div>
    </div>
  )
}
