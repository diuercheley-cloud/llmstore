import { useState, useEffect } from 'react'
import { FileText, Plus, Search, Edit3, Copy, Clock } from 'lucide-react'
import api from '../../lib/api'
import { LoadingCard } from '../../components/ui-feedback'

interface PromptTemplate {
  id: string
  name: string
  description?: string
  version: number
  content: string
  variables: string[]
  created_at: string
  updated_at: string
}

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<PromptTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<PromptTemplate | null>(null)

  useEffect(() => {
    api.listPrompts?.()
      .then(setPrompts)
      .catch(() => setPrompts([]))
      .finally(() => setLoading(false))
  }, [])

  const filtered = prompts.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase())
  )

  if (loading) return <LoadingCard />

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FileText className="w-6 h-6 text-primary" /> Prompt Templates
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Create, version, and manage prompt templates for your agents.
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90">
          <Plus className="w-4 h-4" /> New Prompt
        </button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search prompts..."
          className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-background"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      <div className="grid gap-4">
        {filtered.map(p => (
          <div
            key={p.id}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              selected?.id === p.id
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/50'
            }`}
            onClick={() => setSelected(p)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="font-semibold flex items-center gap-2">
                  {p.name}
                  <span className="text-xs bg-secondary px-2 py-0.5 rounded-full">
                    v{p.version}
                  </span>
                </h3>
                {p.description && (
                  <p className="text-sm text-muted-foreground mt-1">{p.description}</p>
                )}
              </div>
              <div className="flex items-center gap-2 text-muted-foreground">
                <button className="p-1.5 hover:bg-secondary rounded-lg" title="Edit">
                  <Edit3 className="w-4 h-4" />
                </button>
                <button className="p-1.5 hover:bg-secondary rounded-lg" title="Duplicate">
                  <Copy className="w-4 h-4" />
                </button>
              </div>
            </div>
            {p.variables?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {p.variables.map(v => (
                  <span key={v} className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 px-2 py-0.5 rounded-full">
                    {'{{' + v + '}}'}
                  </span>
                ))}
              </div>
            )}
            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" /> Updated {new Date(p.updated_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        ))}
        {filtered.length === 0 && !loading && (
          <div className="text-center py-12 text-muted-foreground">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No prompt templates yet.</p>
          </div>
        )}
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setSelected(null)}>
          <div className="max-w-2xl w-full bg-card rounded-2xl p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold">{selected.name}</h2>
              <button onClick={() => setSelected(null)} className="text-muted-foreground hover:text-foreground">&times;</button>
            </div>
            <pre className="p-4 bg-muted rounded-lg text-sm font-mono whitespace-pre-wrap max-h-64 overflow-auto">
              {selected.content}
            </pre>
            {selected.variables?.length > 0 && (
              <div>
                <p className="text-sm font-semibold mb-1">Variables</p>
                <div className="flex flex-wrap gap-1.5">
                  {selected.variables.map(v => (
                    <span key={v} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">{'{{' + v + '}}'}</span>
                  ))}
                </div>
              </div>
            )}
            <button className="w-full py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90">
              Use in Agent
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
