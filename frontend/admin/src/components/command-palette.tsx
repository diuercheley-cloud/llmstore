import { useEffect, useState } from "react"
import { Search, Command, Users, Box, Cpu, Activity, Shield, LogOut, X } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { useAuthStore } from "../store/useAuthStore"

const shortcuts = [
  { name: "Ir para Hub", keys: "G H", icon: <Shield className="w-4 h-4" />, path: "/" },
  { name: "Ver Clientes", keys: "G C", icon: <Users className="w-4 h-4" />, path: "/clients" },
  { name: "Ver Modelos", keys: "G M", icon: <Box className="w-4 h-4" />, path: "/models" },
  { name: "Ver Backends", keys: "G B", icon: <Cpu className="w-4 h-4" />, path: "/backends" },
  { name: "Ver Operações", keys: "G O", icon: <Activity className="w-4 h-4" />, path: "/operations" },
  { name: "Sair", keys: "L O", icon: <LogOut className="w-4 h-4" />, action: "logout" },
]

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState("")
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        setIsOpen((prev) => !prev)
      }
      if (e.key === "Escape") {
        setIsOpen(false)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  if (!isOpen) return null

  const filtered = shortcuts.filter(s => 
    s.name.toLowerCase().includes(search.toLowerCase())
  )

  const handleAction = (shortcut: typeof shortcuts[0]) => {
    if (shortcut.path) {
      navigate(shortcut.path)
    } else if (shortcut.action === "logout") {
      logout()
    }
    setIsOpen(false)
  }

  return (
    <div 
      className="fixed inset-0 z-[100] bg-background/80 backdrop-blur-sm flex items-start justify-center pt-[15vh] p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="command-palette-title"
    >
      <div className="w-full max-w-2xl bg-card border border-border rounded-3xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
        <div className="p-4 border-b border-border flex items-center gap-3">
          <Search className="w-5 h-5 text-muted-foreground" aria-hidden="true" />
          <input 
            autoFocus
            type="text" 
            placeholder="Digite um comando ou busque..." 
            className="flex-1 bg-transparent border-none outline-none text-lg text-foreground placeholder:text-muted-foreground"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Buscar comandos"
          />
          <kbd className="hidden sm:inline-flex h-5 select-none items-center gap-1 rounded border border-border bg-secondary px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
            <span className="text-xs">ESC</span>
          </kbd>
          <button 
            onClick={() => setIsOpen(false)}
            className="p-1 hover:bg-secondary rounded-lg transition-colors"
            aria-label="Fechar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto p-2">
          <h2 id="command-palette-title" className="px-3 py-2 text-xs font-bold text-muted-foreground uppercase tracking-widest">Atalhos Disponíveis</h2>
          <div className="space-y-1">
            {filtered.map((shortcut) => (
              <button
                key={shortcut.name}
                onClick={() => handleAction(shortcut)}
                className="w-full flex items-center justify-between px-3 py-3 rounded-xl hover:bg-primary/10 hover:text-primary text-foreground transition-all group focus-visible:bg-primary/10 focus-visible:text-primary outline-none"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-secondary rounded-lg group-hover:bg-background transition-colors">
                    {shortcut.icon}
                  </div>
                  <span className="font-semibold">{shortcut.name}</span>
                </div>
                <div className="flex gap-1">
                  {shortcut.keys.split(" ").map(key => (
                    <kbd key={key} className="min-w-[1.5rem] h-5 px-1 inline-flex items-center justify-center rounded border border-border bg-secondary font-mono text-[10px] font-bold text-muted-foreground">
                      {key}
                    </kbd>
                  ))}
                </div>
              </button>
            ))}
            {filtered.length === 0 && (
              <div className="px-3 py-8 text-center text-muted-foreground">
                Nenhum comando encontrado para "{search}"
              </div>
            )}
          </div>
        </div>

        <div className="p-4 border-t border-border bg-secondary/30 flex items-center justify-between text-[10px] text-muted-foreground font-bold uppercase tracking-wider">
          <div className="flex gap-4">
            <span className="flex items-center gap-1"><Command className="w-3 h-3" /> para selecionar</span>
            <span className="flex items-center gap-1"><kbd className="border border-border px-1 rounded">ESC</kbd> para fechar</span>
          </div>
          <div>Comandos Rápidos</div>
        </div>
      </div>
    </div>
  )
}
