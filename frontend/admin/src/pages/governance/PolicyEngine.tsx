import { useQuery, useMutation } from '@tanstack/react-query'
import api from '../../lib/api'
import { ShieldAlert, ShieldCheck, Activity, Terminal, Play, Info, AlertCircle, CheckCircle2, FlaskConical, Gavel } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

export default function PolicyEngine() {
  const [testContext, setTestContext] = useState<any>({
    tenant_id: 'default',
    action_type: 'tool_call',
    tool_name: 'search_web',
    risk_score: 0.5,
    data_classification: 'public'
  })
  const [dryRunResult, setDryRunResult] = useState<any>(null)

  const { data: engines, isLoading } = useQuery({
    queryKey: ['policy-engines'],
    queryFn: async () => {
      const res = await api.get('/admin/policies')
      return res.data
    }
  })

  const dryRunMutation = useMutation({
    mutationFn: async (context: any) => {
      const res = await api.post('/admin/policies/dry-run', context)
      return res.data
    },
    onSuccess: (data) => {
      setDryRunResult(data)
      toast.success('Política avaliada')
    },
    onError: () => {
      toast.error('Falha na avaliação')
    }
  })

  const getResultIcon = (result: string) => {
    switch (result) {
      case 'allow': return <ShieldCheck className="w-4 h-4 text-primary" />
      case 'deny': return <ShieldAlert className="w-4 h-4 text-destructive" />
      default: return <AlertCircle className="w-4 h-4 text-warning" />
    }
  }

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-foreground flex items-center gap-3">
            <Gavel className="w-8 h-8 text-primary" /> POLICY ENGINE
          </h1>
          <p className="text-muted-foreground mt-1">Gestão declarativa de governança, permissões e conformidade técnica.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
            <h2 className="font-bold flex items-center gap-2 mb-6 text-lg">
              <Activity className="w-5 h-5 text-primary" /> Motores Ativos
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {engines?.map((e: any) => (
                <div key={e.name} className="p-4 bg-secondary/30 border border-border rounded-2xl flex items-center justify-between">
                  <div>
                    <div className="font-black uppercase text-xs tracking-widest">{e.name}</div>
                    <div className="text-[10px] text-muted-foreground uppercase">{e.status}</div>
                  </div>
                  <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                </div>
              ))}
            </div>
          </div>

          <div className="bg-primary/5 border border-primary/10 rounded-3xl p-6">
            <h2 className="font-bold flex items-center gap-2 mb-6">
              <FlaskConical className="w-5 h-5 text-primary" /> Simulador de Política (Dry-Run)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div className="space-y-4">
                <div>
                  <label className="text-[10px] font-black uppercase text-muted-foreground mb-1 block">Ação</label>
                  <select 
                    className="w-full bg-background border border-border rounded-xl px-4 py-2 text-sm"
                    value={testContext.action_type}
                    onChange={(e) => setTestContext({...testContext, action_type: e.target.value})}
                  >
                    <option value="tool_call">Tool Call</option>
                    <option value="inference">Inference</option>
                    <option value="memory_access">Memory Access</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-black uppercase text-muted-foreground mb-1 block">Risk Score (0.0 - 1.0)</label>
                  <input 
                    type="range" min="0" max="1" step="0.1"
                    className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                    value={testContext.risk_score}
                    onChange={(e) => setTestContext({...testContext, risk_score: parseFloat(e.target.value)})}
                  />
                  <div className="text-right text-[10px] font-bold text-primary mt-1">{testContext.risk_score}</div>
                </div>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-[10px] font-black uppercase text-muted-foreground mb-1 block">Data Classification</label>
                  <select 
                    className="w-full bg-background border border-border rounded-xl px-4 py-2 text-sm"
                    value={testContext.data_classification}
                    onChange={(e) => setTestContext({...testContext, data_classification: e.target.value})}
                  >
                    <option value="public">Public</option>
                    <option value="internal">Internal</option>
                    <option value="secret">Secret</option>
                  </select>
                </div>
                <button 
                  onClick={() => dryRunMutation.mutate(testContext)}
                  disabled={dryRunMutation.isPending}
                  className="w-full mt-auto py-3 bg-primary text-primary-foreground rounded-xl font-black text-sm shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50"
                >
                  {dryRunMutation.isPending ? 'AVALIANDO...' : 'EXECUTAR DRY-RUN'}
                </button>
              </div>
            </div>

            {dryRunResult && (
              <div className="bg-background border border-border rounded-2xl p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-4">
                  <h3 className="font-bold text-sm">Decisões Multi-Engine</h3>
                  <span className={`text-[10px] font-black px-2 py-0.5 rounded ${dryRunResult.is_safe ? 'bg-primary/10 text-primary' : 'bg-destructive/10 text-destructive'}`}>
                    {dryRunResult.is_safe ? 'SAFE' : 'RISKY'}
                  </span>
                </div>
                <div className="space-y-3">
                  {dryRunResult.decisions.map((d: any, idx: number) => (
                    <div key={idx} className="p-3 bg-secondary/20 rounded-xl border border-border flex items-start gap-3">
                      <div className="mt-0.5">{getResultIcon(d.result)}</div>
                      <div className="flex-1">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-[10px] font-black uppercase text-primary">{d.engine}</span>
                          <span className="text-[10px] font-bold text-muted-foreground font-mono">{d.result}</span>
                        </div>
                        <p className="text-xs font-medium text-foreground">{d.reason}</p>
                        {d.explanation && <p className="text-[10px] text-muted-foreground mt-1 italic">"{d.explanation}"</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-card border border-border rounded-3xl p-6">
            <h2 className="font-bold flex items-center gap-2 mb-4">
              <Info className="w-5 h-5 text-muted-foreground" /> Governança Avançada
            </h2>
            <div className="space-y-4 text-[11px] leading-relaxed">
              <div className="flex gap-3">
                <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
                <span>Integração com <strong>Open Policy Agent (Rego)</strong> para regras complexas baseadas em JSON.</span>
              </div>
              <div className="flex gap-3">
                <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
                <span>Suporte experimental ao framework <strong>Cedar</strong> da AWS para autorização de fine-grained.</span>
              </div>
              <div className="flex gap-3">
                <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
                <span>Garantia de <strong>Fallback Seguro</strong>: falha do motor externo resulta em bloqueio (Fail-Closed) ou builtin.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
