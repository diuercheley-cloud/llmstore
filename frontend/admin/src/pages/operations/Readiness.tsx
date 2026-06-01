import { useQuery, useMutation } from '@tanstack/react-query'
import api from '../../lib/api'
import { CheckCircle2, XCircle, RefreshCw, ClipboardList } from 'lucide-react'
import ActionPanel from '../../components/operations/ActionPanel'

export default function Readiness() {
  const { data: report, isLoading, refetch } = useQuery({
    queryKey: ['readiness-report'],
    queryFn: async () => {
      const res = await api.get('/admin/operations/readiness-report')
      return res.data
    }
  })

  const runMutation = useMutation({
    mutationFn: async () => {
      return api.post('/admin/operations/run-readiness')
    },
    onSuccess: () => {
      refetch()
    }
  })

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-black text-foreground mb-2">Operational <span className="text-primary">Readiness</span></h1>
          <p className="text-muted-foreground font-medium">Verificação de pré-requisitos e integridade da stack.</p>
        </div>
        <button 
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
          className="bg-foreground text-background px-6 py-3 rounded-2xl font-bold flex items-center gap-2 hover:bg-foreground transition-colors shadow-xl shadow-slate-900/20 disabled:opacity-50"
        >
          <RefreshCw className={`w-5 h-5 ${runMutation.isPending ? 'animate-spin' : ''}`} />
          Recalcular Readiness
        </button>
      </div>

      <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm mb-10">
        <div className="p-8 border-b border-border flex items-center gap-6">
          <div className={`p-4 rounded-3xl ${report?.overall_status === 'ready' ? 'bg-primary/10 text-primary' : 'bg-destructive/10 text-destructive'}`}>
            <ClipboardList className="w-8 h-8" />
          </div>
          <div>
            <div className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-1">Estado da Stack</div>
            <div className="text-3xl font-black text-foreground uppercase">{report?.overall_status || 'UNKNOWN'}</div>
          </div>
        </div>
        
        <div className="divide-y divide-border">
          {report?.checks.map((check: any) => (
            <div key={check.name} className="p-6 flex items-center justify-between hover:bg-secondary/50 transition-colors">
              <span className="font-bold text-foreground">{check.name}</span>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-black uppercase tracking-widest ${check.status === 'pass' ? 'text-primary' : 'text-destructive'}`}>
                  {check.status === 'pass' ? 'SUCCESS' : 'FAILED'}
                </span>
                {check.status === 'pass' ? (
                  <CheckCircle2 className="w-5 h-5 text-primary" />
                ) : (
                  <XCircle className="w-5 h-5 text-destructive" />
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <ActionPanel title="Manutenção Preventiva" description="Ações para garantir a saúde a longo prazo.">
        <button className="bg-card border border-border text-foreground px-4 py-2 rounded-xl font-bold text-sm hover:bg-secondary transition-colors">
          Limpar Caches de Resposta
        </button>
        <button className="bg-card border border-border text-foreground px-4 py-2 rounded-xl font-bold text-sm hover:bg-secondary transition-colors">
          Compactar Base de Dados
        </button>
        <button className="bg-card border border-border text-foreground px-4 py-2 rounded-xl font-bold text-sm hover:bg-secondary transition-colors">
          Download Readiness Report (PDF)
        </button>
      </ActionPanel>
    </div>
  )
}
