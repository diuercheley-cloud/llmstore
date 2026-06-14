import { useQuery, useMutation } from '@tanstack/react-query'
import { Inbox, Trash2, RefreshCw, AlertTriangle, Loader2, Bot, Clock } from 'lucide-react'
import api from '../../lib/api'
import { toast } from 'sonner'

export default function WorkerDLQ() {
  const dlqItems = useQuery({
    queryKey: ['worker-dlq'],
    queryFn: () => api.listDlqMessages(),
    refetchInterval: 10000, // Refresh every 10s
  })

  const retryMutation = useMutation({
    mutationFn: (id: string) => api.retryDlqItem(id),
    onSuccess: () => {
      toast.success('Tarefa enviada para reprocessamento.')
      dlqItems.refetch()
    },
    onError: (err: any) => toast.error(err?.message || 'Falha ao tentar novamente')
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteDlqItem(id),
    onSuccess: () => {
      toast.success('Tarefa descartada.')
      dlqItems.refetch()
    },
    onError: (err: any) => toast.error(err?.message || 'Falha ao descartar')
  })

  const handleRetry = (id: string) => {
    if (confirm('Deseja realmente tentar reprocessar esta tarefa?')) {
      retryMutation.mutate(id)
    }
  }

  const handleDelete = (id: string) => {
    if (confirm('Tem certeza que deseja descartar permanentemente esta tarefa falha?')) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-foreground flex items-center gap-3">
            <Inbox className="w-8 h-8 text-primary" /> Worker DLQ
          </h1>
          <p className="text-muted-foreground mt-1">Monitoramento de tarefas falhas e gestão de Dead Letter Queue.</p>
        </div>
        <div className="flex items-center gap-3">
           <button 
             onClick={() => dlqItems.refetch()}
             className="p-3 bg-secondary rounded-xl hover:bg-secondary/80 transition-colors"
           >
             <RefreshCw className={`w-5 h-5 ${dlqItems.isFetching ? 'animate-spin' : ''}`} />
           </button>
        </div>
      </div>

      <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-border bg-secondary/5 font-black uppercase text-xs tracking-wider flex items-center justify-between">
          <span>Failed background tasks</span>
          <span className="badge bg-red-100 text-red-700">{dlqItems.data?.length || 0}</span>
        </div>
        
        <div className="divide-y divide-border">
          {dlqItems.isLoading ? (
            <div className="p-12 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
          ) : dlqItems.data?.length === 0 ? (
            <div className="p-20 text-center flex flex-col items-center gap-4">
              <div className="p-4 bg-emerald-50 text-emerald-600 rounded-full">
                <Bot size={40} />
              </div>
              <div>
                <h3 className="font-black text-lg">Tudo limpo!</h3>
                <p className="text-muted-foreground text-sm">Nenhuma tarefa falha na fila de processamento.</p>
              </div>
            </div>
          ) : dlqItems.data?.map((msg: any) => (
            <div key={msg.id} className="px-6 py-6 flex flex-col sm:flex-row sm:items-center justify-between gap-6 hover:bg-secondary/5 transition-colors">
              <div className="space-y-2 flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-primary font-black bg-primary/10 px-2 py-0.5 rounded uppercase tracking-tighter">
                    {msg.job_id.slice(0, 8)}
                  </span>
                  <span className="text-xs text-muted-foreground flex items-center gap-1 font-medium">
                    <Clock size={12} /> {new Date(msg.failed_at).toLocaleString()}
                  </span>
                </div>
                <div className="text-sm font-bold text-slate-900 line-clamp-1">{msg.last_error || 'Erro desconhecido'}</div>
                <div className="text-[10px] text-slate-400 font-mono flex items-center gap-2">
                  <span>DLQ_ID: {msg.id}</span>
                  <span>•</span>
                  <span>TENANT: {msg.tenant_id}</span>
                </div>
              </div>
              
              <div className="flex items-center gap-2 shrink-0">
                <button 
                  onClick={() => handleRetry(msg.id)}
                  disabled={retryMutation.isPending}
                  className="btn btn-outline py-2 px-4 text-xs font-black flex items-center gap-2 border-primary/20 text-primary hover:bg-primary/5"
                >
                  <RefreshCw size={14} /> Retry
                </button>
                <button 
                  onClick={() => handleDelete(msg.id)}
                  disabled={deleteMutation.isPending}
                  className="btn btn-danger py-2 px-4 text-xs font-black flex items-center gap-2"
                >
                  <Trash2 size={14} /> Discard
                </button>
              </div>
            </div>
          ))}
          {dlqItems.isError && (
             <div className="p-12 text-center bg-amber-50 text-amber-700">
               <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
               <p className="font-bold">Falha ao carregar DLQ</p>
               <p className="text-xs">Verifique sua conexão ou permissões administrativas.</p>
             </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
         <div className="p-6 rounded-3xl border border-border bg-card space-y-4 shadow-sm border-l-4 border-l-primary">
            <h3 className="font-black flex items-center gap-2"><Bot className="w-5 h-5 text-primary" /> Worker Visibility</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
               As tarefas nesta fila excederam o número máximo de retentativas automáticas (default: 3). 
               O reprocessamento manual reiniciará o contador de tentativas.
            </p>
         </div>
         <div className="p-6 rounded-3xl border border-border bg-card space-y-4 shadow-sm border-l-4 border-l-emerald-500">
            <h3 className="font-black flex items-center gap-2"><ShieldCheck className="w-5 h-5 text-emerald-500" /> Operational Safety</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
               O descarte de tarefas é irreversível e pode resultar em inconsistência de estado para o agente. 
               Verifique os logs detalhados antes de expurgar a DLQ.
            </p>
         </div>
      </div>
    </div>
  )
}

function ShieldCheck({ className, size }: { className?: string, size?: number }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={size || 24} height={size || 24} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  )
}
