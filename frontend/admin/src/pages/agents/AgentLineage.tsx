import { useState, useEffect } from 'react'
import { GitBranch, CheckCircle2, Clock, Search, Server, GitCommit, User, Bot, Loader2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import { LoadingCard } from '../../components/ui-feedback'

interface LifecycleEvent {
  id: string
  event_type: string
  from_status: string
  to_status: string
  performed_by: string
  notes: string | null
  created_at: string
}

interface AgentVersion {
  id: string
  version: string
  created_at: string
}

interface LineageData {
  agent_id: string
  events: LifecycleEvent[]
  versions: AgentVersion[]
}

export default function AgentLineage() {
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)

  // Fetch agent list from registry
  const { data: registry = [], isLoading: registryLoading } = useQuery({
    queryKey: ['agent-registry'],
    queryFn: () => api.listAgentRegistry()
  })

  // Fetch lineage for selected agent
  const { data: lineage, isLoading: lineageLoading } = useQuery<LineageData>({
    queryKey: ['agent-lineage', selectedAgentId],
    queryFn: () => api.getAgentLineage(selectedAgentId!),
    enabled: !!selectedAgentId
  })

  if (registryLoading) return <LoadingCard />

  const getEventIcon = (type: string) => {
     switch(type) {
        case 'approve': return <CheckCircle2 size={14} className="text-emerald-500" />
        case 'submit_review': return <Clock size={14} className="text-amber-500" />
        case 'activate': return <Rocket size={14} className="text-primary" />
        default: return <GitCommit size={14} className="text-muted-foreground" />
     }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 p-6">
      <header>
        <div className="flex items-center gap-2 text-primary font-bold uppercase tracking-wider text-[10px] mb-2">
          <GitBranch className="w-4 h-4" />
          Version Integrity & Provenance
        </div>
        <h1 className="text-4xl font-black tracking-tight text-foreground">Agent <span className="text-primary">Lineage</span></h1>
        <p className="text-muted-foreground mt-2 font-medium">Histórico completo de alterações, aprovações e auditoria de versões.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Sidebar: Agent List */}
        <div className="lg:col-span-1 space-y-4">
           <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
              <h2 className="text-xs font-black uppercase tracking-widest text-muted-foreground mb-4">Selecionar Agente</h2>
              <div className="relative mb-4">
                 <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                 <input 
                    type="text" 
                    placeholder="Filtrar registry..." 
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 focus:ring-primary/20"
                 />
              </div>
              <div className="space-y-2 max-h-[500px] overflow-y-auto pr-2">
                 {registry.map((agent: any) => (
                    <button
                       key={agent.id}
                       onClick={() => setSelectedAgentId(agent.id)}
                       className={`w-full text-left p-4 rounded-2xl border transition-all flex items-center gap-3 group ${
                          selectedAgentId === agent.id 
                             ? 'border-primary bg-primary/5 shadow-sm' 
                             : 'border-transparent hover:bg-muted'
                       }`}
                    >
                       <div className={`p-2 rounded-xl ${selectedAgentId === agent.id ? 'bg-primary text-white' : 'bg-muted text-muted-foreground group-hover:bg-background'}`}>
                          <Server className="w-4 h-4" />
                       </div>
                       <div>
                          <div className="font-bold text-sm text-foreground">{agent.name}</div>
                          <div className="text-[10px] font-mono text-muted-foreground opacity-60 uppercase">{agent.id.slice(0, 8)}</div>
                       </div>
                    </button>
                 ))}
                 {registry.length === 0 && <div className="text-center py-10 text-xs text-muted-foreground italic">Nenhum agente no registry.</div>}
              </div>
           </div>
        </div>

        {/* Main Content: Timeline */}
        <div className="lg:col-span-2">
           {!selectedAgentId ? (
              <div className="h-full flex flex-col items-center justify-center bg-card border border-dashed border-border rounded-[40px] p-20 text-center text-muted-foreground">
                 <div className="p-6 bg-muted rounded-full mb-6">
                    <GitBranch className="w-12 h-12 opacity-20" />
                 </div>
                 <h3 className="text-xl font-bold text-foreground">Aguardando seleção</h3>
                 <p className="max-w-xs mt-2 text-sm">Escolha um agente na lista lateral para visualizar a linha do tempo de alterações e linhagem de dados.</p>
              </div>
           ) : lineageLoading ? (
              <div className="p-20 flex justify-center"><Loader2 className="w-10 h-10 animate-spin text-primary" /></div>
           ) : (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                 <div className="bg-card border border-border rounded-[32px] p-8 shadow-sm">
                    <div className="flex items-center gap-4 mb-10">
                       <div className="p-3 bg-primary text-white rounded-2xl shadow-lg shadow-primary/20">
                          <GitBranch className="w-6 h-6" />
                       </div>
                       <div>
                          <h2 className="text-2xl font-black text-foreground">Timeline <span className="text-primary">Audit</span></h2>
                          <p className="text-sm text-muted-foreground">Rastreabilidade imutável de eventos de ciclo de vida.</p>
                       </div>
                    </div>

                    <div className="relative">
                       {/* Vertical line */}
                       <div className="absolute left-[15px] top-2 bottom-0 w-px bg-gradient-to-b from-primary/30 via-border to-transparent" />

                       <div className="space-y-10">
                          {lineage?.events.map((event, i) => (
                             <div key={event.id} className="flex gap-6 relative">
                                <div className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-sm ${
                                   i === 0 ? 'bg-primary text-white scale-110 ring-4 ring-primary/10' : 'bg-muted text-muted-foreground'
                                }`}>
                                   {getEventIcon(event.event_type)}
                                </div>
                                <div className="flex-1 pt-0.5">
                                   <div className="flex items-center justify-between mb-1">
                                      <div className="flex items-center gap-2">
                                         <span className="font-black text-xs uppercase tracking-tight text-foreground">
                                            {event.event_type.replace(/_/g, ' ')}
                                         </span>
                                         <span className="text-[10px] font-black text-muted-foreground opacity-40 uppercase tracking-tighter">
                                            {event.from_status} → {event.to_status}
                                         </span>
                                      </div>
                                      <span className="text-[10px] font-mono text-muted-foreground opacity-50">
                                         {new Date(event.created_at).toLocaleString()}
                                      </span>
                                   </div>
                                   <div className="bg-muted/30 border border-border rounded-2xl p-4 mt-2">
                                      <p className="text-sm text-foreground/80 leading-relaxed font-medium">
                                         {event.notes || 'Nenhuma observação registrada para este evento.'}
                                      </p>
                                      <div className="mt-4 flex items-center gap-2">
                                         <div className="w-5 h-5 rounded-full bg-background border border-border flex items-center justify-center">
                                            <User size={10} className="text-muted-foreground" />
                                         </div>
                                         <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Performed by {event.performed_by}</span>
                                      </div>
                                   </div>
                                </div>
                             </div>
                          ))}
                          
                          {lineage?.events.length === 0 && (
                             <div className="text-center py-10">
                                <p className="text-sm text-muted-foreground italic">Nenhum evento de ciclo de vida registrado para este agente.</p>
                             </div>
                          )}
                       </div>
                    </div>
                 </div>
                 
                 {/* Versions Summary */}
                 <div className="bg-card border border-border rounded-[32px] p-8 shadow-sm">
                    <h3 className="text-xs font-black uppercase tracking-widest text-muted-foreground mb-6">Versões Registradas</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                       {lineage?.versions.map(v => (
                          <div key={v.id} className="p-4 rounded-2xl border border-border bg-muted/20 flex items-center justify-between group hover:border-primary/30 transition-all">
                             <div className="flex items-center gap-3">
                                <div className="p-2 bg-background border border-border rounded-xl text-primary group-hover:bg-primary group-hover:text-white transition-all">
                                   <GitCommit size={16} />
                                </div>
                                <div>
                                   <div className="font-bold text-sm">v{v.version}</div>
                                   <div className="text-[10px] text-muted-foreground">{new Date(v.created_at).toLocaleDateString()}</div>
                                </div>
                             </div>
                             <div className="text-[10px] font-mono opacity-30 group-hover:opacity-100 transition-all uppercase">{v.id.slice(0, 8)}</div>
                          </div>
                       ))}
                    </div>
                 </div>
              </div>
           )}
        </div>
      </div>
    </div>
  )
}

function Rocket({ size, className }: { size: number, className: string }) {
  return (
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className={className}
    >
      <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.71-2.13.09-3l-3.09-3Z" />
      <path d="M12 15s-4 4-5 3c-1-1 3-5 3-5" />
      <path d="M22 2s-5.5.5-8.5 2.5a14.28 14.28 0 0 0-4 4.5c-.5 1.5-1 4.5-1 4.5s3-.5 4.5-1a14.28 14.28 0 0 0 4.5-4C21.5 7.5 22 2 22 2Z" />
      <path d="M17 7l-2 2" />
    </svg>
  )
}
