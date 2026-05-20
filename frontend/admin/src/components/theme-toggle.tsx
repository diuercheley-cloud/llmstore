import { Moon, Sun, Monitor } from "lucide-react"
import { useTheme } from "./theme-provider"

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <div 
      className="flex items-center gap-1 bg-muted p-1 rounded-lg border border-border"
      role="group"
      aria-label="Seletor de tema"
    >
      <button
        onClick={() => setTheme("light")}
        className={`p-1.5 rounded-md transition-all focus-visible:ring-2 focus-visible:ring-primary ${
          theme === "light"
            ? "bg-card text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground"
        }`}
        aria-pressed={theme === "light"}
        aria-label="Tema claro"
        title="Tema claro"
      >
        <Sun className="w-4 h-4" aria-hidden="true" />
      </button>
      <button
        onClick={() => setTheme("dark")}
        className={`p-1.5 rounded-md transition-all focus-visible:ring-2 focus-visible:ring-primary ${
          theme === "dark"
            ? "bg-card text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground"
        }`}
        aria-pressed={theme === "dark"}
        aria-label="Tema escuro"
        title="Tema escuro"
      >
        <Moon className="w-4 h-4" aria-hidden="true" />
      </button>
      <button
        onClick={() => setTheme("system")}
        className={`p-1.5 rounded-md transition-all focus-visible:ring-2 focus-visible:ring-primary ${
          theme === "system"
            ? "bg-card text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground"
        }`}
        aria-pressed={theme === "system"}
        aria-label="Tema do sistema"
        title="Tema do sistema"
      >
        <Monitor className="w-4 h-4" aria-hidden="true" />
      </button>
    </div>
  )
}
