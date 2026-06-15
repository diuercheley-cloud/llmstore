import { useState, useEffect } from 'react'
import { FileText, Plus, Search, Edit3, Copy, Clock, X, Loader2 } from 'lucide-react'
import api from '../../lib/api'
import { LoadingCard } from '../../components/ui-feedback'

interface PromptTemplate {
  id: string
  name: string
  description?: string
  version?: number
  variables_count?: number
  created_at: string
  updated_at: string
}

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<PromptTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<PromptTemplate | null>(null)
  
  // New Prompt Modal State
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  const fetchPrompts = () => {
    setLoading(true)
    api.listPrompts?.()
      .then(setPrompts)
      .catch(() => setPrompts([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    void Promise.resolve().then(() => fetchPrompts())
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newName) return
    
    setIsSaving(true)
    try {
      await api.createPromptTemplate?.({
        name: newName,
        description: newDesc
      })
      setIsModalOpen(false)
      setNewName('')
      setNewDesc('')
      fetchPrompts()
    } catch (err) {
      console.error("Failed to create prompt", err)
      alert("Erro ao criar prompt. Verifique se as permissões estão corretas.")
    } finally {
      setIsSaving(false)
    }
  }

  const filtered = prompts.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase())
  )

  if (loading && prompts.length === 0) return <LoadingCard />

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
        <button 
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-all shadow-sm"
        >
          <Plus className="w-4 h-4" /> New Prompt
        </button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search prompts..."
          className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20 outline-none"
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
                : 'border-border hover:border-primary/50 bg-card'
            }`}
            onClick={() => setSelected(p)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="font-semibold flex items-center gap-2 text-foreground">
                  {p.name}
                  {p.variables_count !== undefined && (
                     <span className="text-[10px] font-bold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full uppercase tracking-tighter">
                       {p.variables_count} variables
                     </span>
                  )}
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
            <div className="flex items-center gap-4 mt-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" /> Updated {new Date(p.updated_at).toLocaleDateString()}
              </span>
              <span className="opacity-40">|</span>
              <span>ID: {p.id.slice(0, 8)}...</span>
            </div>
          </div>
        ))}
        {filtered.length === 0 && !loading && (
          <div className="text-center py-20 bg-muted/30 rounded-3xl border border-dashed border-border">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p className="text-muted-foreground font-medium">No prompt templates yet.</p>
            <button 
              onClick={() => setIsModalOpen(true)}
              className="mt-4 text-primary font-bold text-sm hover:underline"
            >
              Create your first template
            </button>
          </div>
        )}
      </div>

      {/* Creation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-card border border-border rounded-3xl shadow-2xl overflow-hidden">
            <form onSubmit={handleCreate}>
              <div className="p-6 border-b border-border flex justify-between items-center bg-secondary/30">
                <h2 className="text-lg font-black uppercase tracking-tight">New Prompt Template</h2>
                <button type="button" onClick={() => setIsModalOpen(false)} className="text-muted-foreground hover:text-foreground">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6 space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Name</label>
                  <input 
                    autoFocus
                    required
                    type="text" 
                    className="w-full px-4 py-2.5 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary/20 outline-none"
                    placeholder="e.g. customer-service-agent"
                    value={newName}
                    onChange={e => setNewName(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Description</label>
                  <textarea 
                    className="w-full px-4 py-2.5 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary/20 outline-none min-h-[100px]"
                    placeholder="Describe the purpose of this prompt..."
                    value={newDesc}
                    onChange={e => setNewDesc(e.target.value)}
                  />
                </div>
              </div>
              <div className="p-6 bg-secondary/10 border-t border-border flex gap-3">
                <button 
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 py-3 px-4 rounded-xl font-bold text-sm border border-border hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button 
                  disabled={isSaving || !newName}
                  type="submit"
                  className="flex-1 py-3 px-4 rounded-xl font-bold text-sm bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  Create Template
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
