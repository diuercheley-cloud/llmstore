import { useState, useEffect } from 'react'
import { Rocket, CheckCircle2, XCircle, ShieldCheck, Search, Loader2, Server, ArrowRight, Activity, GitBranch } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { LoadingCard } from '../../components/ui-feedback'

interface EnvInfo {
  active_version_id: string | null
  active_version_num: number | null
  deployed_at: string | null
  status: string
}

interface AgentEnvironments {
  agent_id: string
  name: string
  environments: {
    dev: EnvInfo
    staging: EnvInfo
    production: EnvInfo
  }
}

export default function AgentPromotion() {
  const queryClient = useQueryClient()
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [targetEnv, setTargetEnv] = useState<'staging' | 'production'>('staging')

  // Fetch agent list from registry
  const { data: registry = [], isLoading: registryLoading } = useQuery({
    queryKey: ['agent-registry'],
    queryFn: () => api.listAgentRegistry()
  })

  // Fetch environments for selected agent
  const { data: envRaw = [], isLoading: envLoading } = useQuery({
    queryKey: ['agent-environments', selectedAgentId],
    queryFn: () => api.getAgentEnvironments(selectedAgentId!),
    enabled: !!selectedAgentId
  })

  const envData = Array.isArray(envRaw) ? {
     environments: envRaw.reduce((acc: any, curr: any) => {
        acc[curr.environment] = curr.deployed_version;
        return acc;
     }, {})
  } : null;

  const promoteMutation = useMutation({
    mutationFn: (payload: { from: string, to: string, version: string }) => 
      api.promoteAgent(selectedAgentId!, {
        from_environment: payload.from,
        to_environment: payload.to,
        version_id: payload.version,
        approve: true
      }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['agent-environments', selectedAgentId] })
      alert(res.message || "Promoção concluída com sucesso!")
    },
    onError: (err: any) => {
      alert(`Falha na promoção: ${err.message || "Verifique as políticas de segurança."}`)
    }
  })

  if (registryLoading) return <LoadingCard />

  const activeAgent = registry.find((a: any) => a.id === selectedAgentId)

  const getEnvVersion = (env: string) => {
     const info = envData?.environments[env];
     return info ? `v${info.version_tag}` : '---';
  };

  const getEnvDate = (env: string) => {
     const info = envData?.environments[env];
     return info?.deployed_at ? new Date(info.deployed_at).toLocaleDateString() : 'Não implantado';
  };

  const hasVersion = (env: string) => !!envData?.environments[env]?.version_id;

  return (
    <div className="max-w-6xl mx-auto space-y-8 p-6">
      <header>
        <div className="flex items-center gap-2 text-primary font-bold uppercase tracking-wider text-[10px] mb-2">
          <Rocket className="w-4 h-4" />
          Agent Lifecycle Management
        </div>
        <h1 className="text-4xl font-black tracking-tight text-foreground">Promoção de <span className="text-primary">Agentes</span></h1>
        <p className="text-muted-foreground mt-2 font-medium">Mova versões validadas entre ambientes de desenvolvimento, homologação e produção.</p>
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

        {/* Main Content: Promotion Workflow */}
        <div className="lg:col-span-2 space-y-6">
           {!selectedAgentId ? (
              <div className="h-full flex flex-col items-center justify-center bg-card border border-dashed border-border rounded-[40px] p-20 text-center text-muted-foreground">
                 <div className="p-6 bg-muted rounded-full mb-6">
                    <GitBranch className="w-12 h-12 opacity-20" />
                 </div>
                 <h3 className="text-xl font-bold text-foreground">Aguardando seleção</h3>
                 <p className="max-w-xs mt-2 text-sm">Escolha um agente na lista lateral para visualizar o status dos ambientes e promover versões.</p>
              </div>
           ) : envLoading ? (
              <div className="p-20 flex justify-center"><Loader2 className="w-10 h-10 animate-spin text-primary" /></div>
           ) : (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                 {/* Environment Status Grid */}
                 <div className="grid grid-cols-3 gap-4">
                    {(['dev', 'staging', 'production'] as const).map(env => {
                       const versionStr = getEnvVersion(env);
                       const dateStr = getEnvDate(env);
                       const active = hasVersion(env);
                       return (
                          <div key={env} className={`p-5 rounded-3xl border ${active ? 'bg-card border-border shadow-sm' : 'bg-muted/30 border-dashed border-border opacity-60'}`}>
                             <div className="flex items-center justify-between mb-4">
                                <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">{env}</span>
                                <Activity className={`w-3 h-3 ${active ? 'text-emerald-500' : 'text-slate-300'}`} />
                             </div>
                             <div className="font-black text-2xl mb-1">
                                {versionStr}
                             </div>
                             <div className="text-[10px] font-medium text-muted-foreground truncate">
                                {dateStr}
                             </div>
                          </div>
                       )
                    })}
                 </div>

                 {/* Promotion Gate Card */}
                 <div className="bg-card border border-border rounded-[32px] p-8 shadow-sm">
                    <div className="flex items-center justify-between mb-8">
                       <div className="flex items-center gap-4">
                          <div className="p-3 bg-primary text-white rounded-2xl shadow-lg shadow-primary/20">
                             <ShieldCheck className="w-6 h-6" />
                          </div>
                          <div>
                             <h2 className="text-2xl font-black">Promotion <span className="text-primary">Gates</span></h2>
                             <p className="text-sm text-muted-foreground">Validando integridade para o ambiente alvo.</p>
                          </div>
                       </div>
                       <div className="flex bg-muted p-1 rounded-xl">
                          <button 
                             onClick={() => setTargetEnv('staging')}
                             className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${targetEnv === 'staging' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground'}`}
                          >
                             Target: Staging
                          </button>
                          <button 
                             onClick={() => setTargetEnv('production')}
                             className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${targetEnv === 'production' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground'}`}
                          >
                             Target: Production
                          </button>
                       </div>
                    </div>

                    <div className="space-y-3 mb-8">
                       {targetEnv === 'staging' ? (
                          <div className="flex items-start gap-4 p-4 rounded-2xl bg-emerald-500/5 border border-emerald-500/10">
                             <CheckCircle2 className="w-5 h-5 text-emerald-500 mt-0.5 shrink-0" />
                             <div>
                                <div className="font-bold text-sm">Auto-Approval (Development Policy)</div>
                                <div className="text-xs text-muted-foreground">Promoções para staging são automáticas para agilizar o ciclo de feedback.</div>
                             </div>
                          </div>
                       ) : (
                          <>
                             <div className="flex items-start gap-4 p-4 rounded-2xl bg-amber-500/5 border border-amber-500/10">
                                <Activity className="w-5 h-5 text-amber-500 mt-0.5 shrink-0" />
                                <div>
                                   <div className="font-bold text-sm text-amber-900">Security & Compliance Scan</div>
                                   <div className="text-xs text-amber-700/70">O sistema verificará se há credenciais expostas nas instruções do agente.</div>
                                </div>
                             </div>
                             <div className="flex items-start gap-4 p-4 rounded-2xl bg-indigo-500/5 border border-indigo-500/10">
                                <Trophy size={20} className="text-indigo-500 mt-0.5 shrink-0" />
                                <div>
                                   <div className="font-bold text-sm text-indigo-900">Evaluation Baseline</div>
                                   <div className="text-xs text-indigo-700/70">Requer um baseline de avaliação definido para garantir qualidade mínima.</div>
                                </div>
                             </div>
                          </>
                       )}
                    </div>

                    <div className="p-6 bg-muted/30 rounded-3xl border border-border flex items-center justify-between">
                       <div className="flex items-center gap-4">
                          <div className="text-center">
                             <div className="text-[10px] font-black uppercase text-muted-foreground mb-1">Origem</div>
                             <div className="px-3 py-1 bg-background border border-border rounded-lg font-bold text-xs uppercase">{targetEnv === 'staging' ? 'dev' : 'staging'}</div>
                          </div>
                          <ArrowRight className="w-4 h-4 text-muted-foreground mt-4" />
                          <div className="text-center">
                             <div className="text-[10px] font-black uppercase text-muted-foreground mb-1">Destino</div>
                             <div className="px-3 py-1 bg-primary text-white rounded-lg font-bold text-xs uppercase">{targetEnv}</div>
                          </div>
                       </div>

                       <button
                          disabled={promoteMutation.isPending || (targetEnv === 'production' && !hasVersion('staging')) || (targetEnv === 'staging' && !hasVersion('dev'))}
                          onClick={() => {
                             const fromEnv = targetEnv === 'staging' ? 'dev' : 'staging';
                             const versionId = envData?.environments[fromEnv]?.version_id;
                             if (!versionId) return;
                             promoteMutation.mutate({
                                from: fromEnv,
                                to: targetEnv,
                                version: versionId
                             });
                          }}
                          className={`flex items-center gap-2 px-8 py-4 rounded-2xl font-black text-sm transition-all shadow-lg shadow-primary/20 ${
                             promoteMutation.isPending ? 'bg-primary/50 text-white cursor-wait' : 'bg-primary text-white hover:scale-[1.02] active:scale-95'
                          } disabled:opacity-30 disabled:cursor-not-allowed`}
                       >
                          {promoteMutation.isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Rocket className="w-5 h-5" />}
                          Promover Agora
                       </button>
                    </div>
                    {targetEnv === 'production' && !hasVersion('staging') && (
                       <p className="mt-4 text-center text-xs text-destructive font-bold uppercase tracking-tight">Nenhuma versão em staging disponível para promover.</p>
                    )}
                    {targetEnv === 'staging' && !hasVersion('dev') && (
                       <p className="mt-4 text-center text-xs text-destructive font-bold uppercase tracking-tight">Nenhuma versão em dev disponível para promover.</p>
                    )}
                 </div>
              </div>
           )}
        </div>
      </div>
    </div>
  )
}

function Trophy({ size, className }: { size: number, className: string }) {
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
      <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
      <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
      <path d="M4 22h16" />
      <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
      <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 7 22" />
      <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
    </svg>
  )
}
