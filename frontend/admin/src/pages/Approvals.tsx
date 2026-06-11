import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { 
  ShieldAlert, 
  ShieldCheck, 
  Clock, 
  XOctagon, 
  AlertTriangle, 
  Check, 
  X, 
  Eye, 
  RefreshCw, 
  ChevronRight, 
  FileText,
  User,
  SlidersHorizontal,
  ChevronDown,
  Activity,
  Terminal,
  Layers
} from 'lucide-react'
import { toast } from 'sonner'

interface CriticalApproval {
  id: string
  action_type: string
  description: string
  status: 'pending' | 'approved' | 'rejected' | 'expired'
  requested_by: string
  requested_at: string
  decided_by?: string
  decided_at?: string
  decision_reason?: string
  expires_at: string
  payload?: any
  metadata_json?: any
}

export default function Approvals() {
  const queryClient = useQueryClient()
  const [selectedRequest, setSelectedRequest] = useState<CriticalApproval | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [isDecisionModalOpen, setIsDecisionModalOpen] = useState(false)
  const [decisionType, setDecisionType] = useState<'approve' | 'reject' | null>(null)
  const [decisionReason, setDecisionReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Fetch critical approvals
  const { data: requests = [], isLoading, isRefetching, refetch } = useQuery<CriticalApproval[]>({
    queryKey: ['critical-approvals', statusFilter],
    queryFn: async () => {
      const res = await api.get('/admin/approvals', {
        params: statusFilter ? { status: statusFilter } : {}
      })
      return res.data
    }
  })

  // WebSocket for Real-time updates
  useEffect(() => {
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    // Get host, fallback to localhost:8080 if running in dev server on different port without proxy
    let host = window.location.host
    if (host.startsWith('localhost:517')) {
      host = 'localhost:8080'
    }
    const wsUrl = `${wsProto}//${host}/admin/approvals/ws`
    
    let ws: WebSocket | null = null
    let reconnectTimeout: any = null

    const connect = () => {
      console.log('Connecting to approvals WS:', wsUrl)
      ws = new WebSocket(wsUrl)

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('Approvals WS Event:', data)
          
          // Toast notifications based on event type
          if (data.event === 'critical_approval.created') {
            toast.warning(`Nova ação crítica requer aprovação: ${data.action_type.toUpperCase()}`, {
              description: data.description,
              duration: 8000
            })
          } else if (data.event === 'critical_approval.approved') {
            toast.success(`Ação crítica aprovada: ${data.action_type.toUpperCase()}`)
          } else if (data.event === 'critical_approval.rejected') {
            toast.error(`Ação crítica rejeitada: ${data.action_type.toUpperCase()}`)
          } else if (data.event === 'critical_approval.expired') {
            toast.info(`Solicitação de aprovação expirou: ${data.action_type.toUpperCase()}`)
          }

          // Trigger refetch
          queryClient.invalidateQueries({ queryKey: ['critical-approvals'] })
          
          // Update selected item details if open
          if (selectedRequest && selectedRequest.id === data.id) {
            refetch().then(res => {
              const updated = res.data?.find(r => r.id === data.id)
              if (updated) setSelectedRequest(updated)
            })
          }
        } catch (err) {
          console.error('Failed to parse websocket message:', err)
        }
      }

      ws.onclose = () => {
        console.log('Approvals WS closed. Reconnecting in 3s...')
        reconnectTimeout = setTimeout(connect, 3000)
      }

      ws.onerror = (err) => {
        console.error('Approvals WS error:', err)
        ws?.close()
      }
    }

    connect()

    return () => {
      if (ws) {
        ws.onclose = null // Prevent reconnect loop on unmount
        ws.close()
      }
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
    }
  }, [queryClient, selectedRequest])

  // Mutations for approvals
  const decisionMutation = useMutation({
    mutationFn: async ({ id, type, reason }: { id: string; type: 'approve' | 'reject'; reason: string }) => {
      const endpoint = `/admin/approvals/${id}/${type}`
      const res = await api.post(endpoint, { decision_reason: reason })
      return res.data
    },
    onSuccess: (data) => {
      toast.success(`Solicitação ${data.status === 'approved' ? 'aprovada' : 'rejeitada'} com sucesso!`)
      queryClient.invalidateQueries({ queryKey: ['critical-approvals'] })
      setSelectedRequest(data)
      setIsDecisionModalOpen(false)
      setDecisionReason('')
      setDecisionType(null)
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail || err.message || 'Erro desconhecido'
      toast.error(`Falha na operação: ${detail}`)
    },
    onSettled: () => {
      setIsSubmitting(false)
    }
  })

  const handleDecisionSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedRequest || !decisionType) return
    setIsSubmitting(true)
    decisionMutation.mutate({
      id: selectedRequest.id,
      type: decisionType,
      reason: decisionReason
    })
  }

  const openDecisionModal = (type: 'approve' | 'reject') => {
    setDecisionType(type)
    setIsDecisionModalOpen(true)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <ShieldCheck className="w-5 h-5 text-emerald-500" />
      case 'rejected':
        return <XOctagon className="w-5 h-5 text-rose-500" />
      case 'expired':
        return <Clock className="w-5 h-5 text-gray-500" />
      default:
        return <AlertTriangle className="w-5 h-5 text-amber-500 animate-pulse" />
    }
  };

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
      case 'rejected':
        return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'
      case 'expired':
        return 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20'
      default:
        return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
    }
  };

  return (
    <div className="flex flex-col gap-6 h-[calc(100vh-7rem)] overflow-hidden">
      {/* Top Header */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-amber-500" />
            Human Approval Center
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Gerencie e conceda permissão de segurança para ações críticas e sensíveis do sistema.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isLoading || isRefetching}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-secondary hover:bg-secondary/80 rounded-xl border border-border transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${(isLoading || isRefetching) ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </header>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 overflow-hidden">
        {/* Left Side: Requests List */}
        <section className="lg:col-span-5 flex flex-col bg-card rounded-2xl border border-border overflow-hidden">
          <div className="p-4 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-secondary/20">
            <h2 className="font-semibold text-sm text-foreground flex items-center gap-2">
              <Activity className="w-4 h-4 text-primary" />
              Solicitações ({requests.length})
            </h2>
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-3.5 h-3.5 text-muted-foreground" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-xs bg-background border border-border rounded-lg px-2 py-1 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">Status: Todos</option>
                <option value="pending">Pendente</option>
                <option value="approved">Aprovado</option>
                <option value="rejected">Rejeitado</option>
                <option value="expired">Expirado</option>
              </select>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-border">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center p-12 text-muted-foreground gap-3">
                <RefreshCw className="w-8 h-8 animate-spin text-primary" />
                <span className="text-sm">Carregando solicitações...</span>
              </div>
            ) : requests.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-12 text-muted-foreground text-center gap-2">
                <ShieldCheck className="w-10 h-10 text-emerald-500/50" />
                <span className="text-sm font-semibold">Tudo Limpo!</span>
                <span className="text-xs">Nenhuma solicitação de aprovação pendente encontrada.</span>
              </div>
            ) : (
              requests.map((req) => (
                <div
                  key={req.id}
                  onClick={() => setSelectedRequest(req)}
                  className={`p-4 flex items-start justify-between gap-3 cursor-pointer hover:bg-secondary/25 transition-all ${
                    selectedRequest?.id === req.id ? 'bg-secondary/40 border-l-2 border-primary' : ''
                  }`}
                >
                  <div className="flex flex-col gap-1.5 min-w-0">
                    <span className="font-mono text-[10px] text-muted-foreground truncate">{req.id}</span>
                    <span className="font-semibold text-sm text-foreground truncate uppercase">{req.action_type}</span>
                    <p className="text-xs text-muted-foreground line-clamp-1">{req.description}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <User className="w-3 h-3" /> {req.requested_by}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium uppercase ${getStatusStyle(req.status)}`}>
                      {req.status}
                    </span>
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Right Side: Details / Action panel */}
        <section className="lg:col-span-7 flex flex-col bg-card rounded-2xl border border-border overflow-hidden">
          {selectedRequest ? (
            <div className="flex flex-col h-full overflow-hidden">
              {/* Request Header Details */}
              <div className="p-5 border-b border-border flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-secondary/10">
                <div className="min-w-0">
                  <span className="font-mono text-xs text-muted-foreground">{selectedRequest.id}</span>
                  <h3 className="text-lg font-bold text-foreground uppercase mt-1 flex items-center gap-2">
                    {getStatusIcon(selectedRequest.status)}
                    {selectedRequest.action_type}
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2.5 py-1 rounded-full border font-bold uppercase ${getStatusStyle(selectedRequest.status)}`}>
                    {selectedRequest.status}
                  </span>
                </div>
              </div>

              {/* Scrollable details contents */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* Description Box */}
                <div className="bg-secondary/20 p-4 rounded-xl border border-border space-y-2">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-primary" /> Descrição da Ação
                  </h4>
                  <p className="text-sm text-foreground">{selectedRequest.description}</p>
                </div>

                {/* Properties list */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border border-border p-3.5 rounded-xl bg-background flex flex-col gap-1">
                    <span className="text-[10px] font-semibold text-muted-foreground uppercase">Solicitado por</span>
                    <span className="text-sm font-medium text-foreground">{selectedRequest.requested_by}</span>
                  </div>
                  <div className="border border-border p-3.5 rounded-xl bg-background flex flex-col gap-1">
                    <span className="text-[10px] font-semibold text-muted-foreground uppercase">Data da Solicitação</span>
                    <span className="text-sm font-medium text-foreground">
                      {new Date(selectedRequest.requested_at).toLocaleString()}
                    </span>
                  </div>
                  {selectedRequest.expires_at && (
                    <div className="border border-border p-3.5 rounded-xl bg-background flex flex-col gap-1">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase">Expira em</span>
                      <span className="text-sm font-medium text-rose-500 flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        {new Date(selectedRequest.expires_at).toLocaleString()}
                      </span>
                    </div>
                  )}
                  {selectedRequest.decided_by && (
                    <div className="border border-border p-3.5 rounded-xl bg-background flex flex-col gap-1">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase">Decidido por</span>
                      <span className="text-sm font-medium text-foreground">
                        {selectedRequest.decided_by} em {selectedRequest.decided_at ? new Date(selectedRequest.decided_at).toLocaleString() : ''}
                      </span>
                    </div>
                  )}
                </div>

                {/* Decision Reason (if exists) */}
                {selectedRequest.decision_reason && (
                  <div className="bg-secondary/15 p-4 rounded-xl border border-border space-y-1.5">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase">Justificativa da Decisão</h4>
                    <p className="text-sm text-foreground">{selectedRequest.decision_reason}</p>
                  </div>
                )}

                {/* Payload details */}
                {selectedRequest.payload && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5 text-primary" /> Parâmetros / Payload
                    </h4>
                    <pre className="text-xs bg-zinc-950 text-zinc-100 p-4 rounded-xl overflow-x-auto border border-zinc-800 font-mono shadow-inner">
                      {JSON.stringify(selectedRequest.payload, null, 2)}
                    </pre>
                  </div>
                )}

                {/* Metadata details */}
                {selectedRequest.metadata_json && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-primary" /> Metadados da Ação
                    </h4>
                    <pre className="text-xs bg-zinc-950 text-zinc-100 p-4 rounded-xl overflow-x-auto border border-zinc-800 font-mono shadow-inner">
                      {JSON.stringify(selectedRequest.metadata_json, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              {/* Action buttons (only for pending) */}
              {selectedRequest.status === 'pending' && (
                <div className="p-4 border-t border-border flex justify-end gap-3 bg-secondary/10">
                  <button
                    onClick={() => openDecisionModal('reject')}
                    className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow-md hover:shadow-lg transition-all"
                  >
                    <X className="w-4 h-4" /> Rejeitar Ação
                  </button>
                  <button
                    onClick={() => openDecisionModal('approve')}
                    className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-md hover:shadow-lg transition-all"
                  >
                    <Check className="w-4 h-4" /> Autorizar Ação
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground text-center p-8 gap-4 bg-secondary/5">
              <ShieldAlert className="w-16 h-16 text-muted-foreground/30" />
              <div>
                <h3 className="font-semibold text-lg">Nenhum Item Selecionado</h3>
                <p className="text-sm max-w-sm mt-1">
                  Selecione uma solicitação de aprovação na lista lateral para visualizar os detalhes e tomar decisões.
                </p>
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Decision Modal */}
      {isDecisionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md bg-card border border-border rounded-2xl shadow-xl overflow-hidden animate-in fade-in duration-200">
            <div className="p-5 border-b border-border flex items-center justify-between">
              <h3 className="font-bold text-foreground">
                {decisionType === 'approve' ? 'Autorizar Ação Crítica' : 'Rejeitar Ação Crítica'}
              </h3>
              <button
                onClick={() => setIsDecisionModalOpen(false)}
                className="p-1 hover:bg-secondary rounded-lg text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleDecisionSubmit}>
              <div className="p-5 space-y-4">
                <p className="text-sm text-muted-foreground">
                  Por favor, forneça uma justificativa para esta decisão. A justificativa será registrada no log de auditoria permanente.
                </p>
                <div className="space-y-2">
                  <label htmlFor="reason-input" className="text-xs font-semibold text-foreground uppercase">Justificativa</label>
                  <textarea
                    id="reason-input"
                    required
                    rows={4}
                    placeholder="Digite a justificativa de segurança..."
                    className="w-full px-3 py-2 text-sm text-foreground bg-background border border-border rounded-xl focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all resize-none"
                    value={decisionReason}
                    onChange={(e) => setDecisionReason(e.target.value)}
                  />
                </div>
              </div>
              <div className="p-4 border-t border-border bg-secondary/15 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsDecisionModalOpen(false)}
                  className="px-4 py-2 text-sm font-semibold hover:bg-secondary rounded-xl transition-colors border border-border text-foreground"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className={`px-5 py-2 rounded-xl text-sm font-bold text-white shadow-md hover:shadow-lg transition-all ${
                    decisionType === 'approve' 
                      ? 'bg-emerald-600 hover:bg-emerald-700' 
                      : 'bg-rose-600 hover:bg-rose-700'
                  }`}
                >
                  {isSubmitting ? 'Processando...' : decisionType === 'approve' ? 'Autorizar' : 'Rejeitar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
