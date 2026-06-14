import { useQuery, useMutation } from '@tanstack/react-query'
import { 
  FlaskConical, 
  Database, 
  Beaker, 
  GitBranch, 
  Loader2, 
  CheckCircle2, 
  Clock, 
  AlertTriangle,
  ExternalLink,
  Play,
  History
} from 'lucide-react'
import api from '../../lib/api'
import { toast } from 'sonner'

export default function MLOpsDashboard() {
  const datasets = useQuery({
    queryKey: ['mlops-datasets'],
    queryFn: () => api.listDatasets(),
  })

  const experiments = useQuery({
    queryKey: ['mlops-experiments'],
    queryFn: () => api.listExperiments(),
  })

  const vllmHealth = useQuery({
    queryKey: ['vllm-health'],
    queryFn: () => api.getVllmHealth(),
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => api.approveDataset(id),
    onSuccess: () => {
      toast.success('Dataset aprovado para produção.')
      datasets.refetch()
    },
    onError: (err: any) => toast.error(err?.message || 'Falha ao aprovar dataset')
  })

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-foreground flex items-center gap-3">
            <FlaskConical className="w-8 h-8 text-primary" /> MLOps Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">Gestão de ciclo de vida de modelos, datasets e experimentos.</p>
        </div>
        <div className={`px-4 py-2 rounded-xl flex items-center gap-2 text-sm font-bold ${vllmHealth.data?.status === 'healthy' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
          {vllmHealth.isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <div className={`w-2 h-2 rounded-full ${vllmHealth.data?.status === 'healthy' ? 'bg-emerald-500' : 'bg-red-500'}`} />}
          vLLM Backend: {vllmHealth.data?.status || 'Unknown'}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Datasets Registry */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card border border-border rounded-3xl overflow-hidden">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/5">
              <h3 className="font-black flex items-center gap-2">
                <Database className="w-5 h-5 text-blue-500" /> Dataset Registry
              </h3>
              <button className="text-xs font-bold text-primary hover:underline">+ New Dataset</button>
            </div>
            <div className="divide-y divide-border">
              {datasets.isLoading ? (
                <div className="p-12 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
              ) : datasets.data?.length === 0 ? (
                <div className="p-12 text-center text-muted-foreground italic">Nenhum dataset registrado.</div>
              ) : datasets.data?.map((d: any) => (
                <div key={d.id} className="px-6 py-4 flex items-center justify-between gap-4 hover:bg-secondary/5 transition-colors">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900">{d.name}</span>
                      {d.is_production && <span className="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded font-black uppercase">Prod</span>}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1 line-clamp-1">{d.description || 'Sem descrição'}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right hidden sm:block">
                      <div className="text-xs font-mono text-slate-500">{d.id.slice(0,8)}</div>
                      <div className="text-[10px] text-slate-400">{new Date(d.created_at).toLocaleDateString()}</div>
                    </div>
                    {!d.is_approved && (
                      <button 
                        onClick={() => approveMutation.mutate(d.id)}
                        disabled={approveMutation.isPending}
                        className="btn btn-outline py-1 px-3 text-xs border-emerald-200 text-emerald-600 hover:bg-emerald-50"
                      >
                        Approve
                      </button>
                    )}
                  </div>
                </div>
              ))}
              {datasets.isError && (
                <div className="p-12 text-center bg-amber-50 text-amber-700">
                  <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="font-bold">Acesso Negado ou MLOps Desabilitado</p>
                  <p className="text-xs">Verifique se <code>mlops_enabled=true</code> nas configurações do sistema.</p>
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-6 rounded-3xl border border-border bg-card space-y-4">
              <h3 className="font-black flex items-center gap-2 text-amber-600">
                <Beaker className="w-5 h-5" /> Fine-tuning Jobs
                <span className="badge bg-amber-100 text-amber-700 ml-auto">BETA</span>
              </h3>
              <p className="text-sm text-muted-foreground italic">Inicie jobs de treinamento e ajuste fino baseados em datasets aprovados.</p>
              <button className="btn btn-primary w-full py-3 rounded-xl font-black flex items-center justify-center gap-2">
                <Play className="w-4 h-4 fill-current" /> Create Training Job
              </button>
            </div>

            <div className="p-6 rounded-3xl border border-border bg-card space-y-4">
              <h3 className="font-black flex items-center gap-2 text-purple-600">
                <GitBranch className="w-5 h-5" /> Model Lineage
              </h3>
              <p className="text-sm text-muted-foreground">Rastreie a origem de cada resposta do modelo até o dataset de treino.</p>
              <div className="flex gap-2 pt-2">
                <input type="text" placeholder="Model ID..." className="input-field py-2 text-xs" />
                <button className="p-2 bg-secondary rounded-lg"><ExternalLink className="w-4 h-4" /></button>
              </div>
            </div>
          </div>
        </div>

        {/* Experiment Tracking */}
        <div className="space-y-6">
          <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-border bg-slate-950 text-white flex items-center justify-between">
              <h3 className="font-black flex items-center gap-2 text-sm uppercase tracking-wider">
                <History className="w-4 h-4" /> Experiment Tracking
              </h3>
            </div>
            <div className="divide-y divide-border max-h-[600px] overflow-y-auto">
              {experiments.isLoading ? (
                <div className="p-8 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
              ) : experiments.data?.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground text-sm">Nenhum experimento ativo.</div>
              ) : experiments.data?.map((e: any) => (
                <div key={e.id} className="p-5 space-y-3 hover:bg-secondary/5 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className="font-black text-sm">{e.name}</span>
                    <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${e.status === 'running' ? 'bg-blue-100 text-blue-700 animate-pulse' : 'bg-slate-100 text-slate-700'}`}>
                      {e.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-secondary/30 p-2 rounded-lg text-center">
                      <div className="text-[10px] text-muted-foreground uppercase">Accuracy</div>
                      <div className="font-black text-sm">{e.metrics?.accuracy?.toFixed(4) || '—'}</div>
                    </div>
                    <div className="bg-secondary/30 p-2 rounded-lg text-center">
                      <div className="text-[10px] text-muted-foreground uppercase">Loss</div>
                      <div className="font-black text-sm">{e.metrics?.loss?.toFixed(4) || '—'}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono">
                    <Clock className="w-3 h-3" /> Started: {new Date(e.started_at).toLocaleString()}
                  </div>
                </div>
              ))}
              {experiments.isError && (
                 <div className="p-8 text-center text-xs text-amber-600 bg-amber-50 italic">
                   Experiment tracking requires MLflow integration configured.
                 </div>
              )}
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-blue-50 border border-blue-100 flex gap-3 shadow-sm">
            <CheckCircle2 className="w-5 h-5 text-blue-500 shrink-0" />
            <p className="text-xs text-blue-700 leading-relaxed font-medium">
              Modelos treinados via MLOps são automaticamente assinados digitalmente e validados pelo <strong>Evidence Center</strong> antes do deploy.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
