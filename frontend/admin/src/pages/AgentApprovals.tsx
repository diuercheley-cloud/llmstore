import { useState } from 'react'
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
  ChevronDown
} from 'lucide-react'
import { toast } from 'sonner'

interface ApprovalRequest {
  id: string
  agent_run_id: string
  task_id?: string
  tool_invocation_id?: string
  risk_level: string
  reason: string
  requested_by: string
  reviewer_role: string
  status: 'pending' | 'approved' | 'rejected' | 'expired' | 'cancelled'
  expires_at: string
  sanitized_context?: any
  decision_reason?: string
  decided_by?: string
  decided_at?: string
  created_at: string
  updated_at: string
}

// Risk Badge component
const RiskBadge = ({ risk }: { risk: string }) => {
  const riskLower = risk.toLowerCase()
  let styles = "bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-900/40 dark:text-slate-300 dark:border-slate-800"
  if (riskLower === 'medium') {
    styles = "bg-amber-100/80 text-amber-800 border-amber-200 dark:bg-amber-950/20 dark:text-amber-300 dark:border-amber-900/50"
  } else if (riskLower === 'high') {
    styles = "bg-orange-100/80 text-orange-800 border-orange-200 dark:bg-orange-950/30 dark:text-orange-400 dark:border-orange-900"
  } else if (riskLower === 'critical') {
    styles = "bg-rose-100/80 text-rose-800 border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-900 animate-pulse"
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-full border ${styles}`}>
      <ShieldAlert className="w-3.5 h-3.5" />
      <span className="capitalize">{risk}</span>
    </span>
  )
}

// Status Badge component
const StatusBadge = ({ status }: { status: string }) => {
  let styles = "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-300"
  let icon = <Clock className="w-3.5 h-3.5" />

  if (status === 'pending') {
    styles = "bg-yellow-500/10 text-yellow-600 border-yellow-500/20 dark:bg-yellow-500/10 dark:text-yellow-400"
  } else if (status === 'approved') {
    styles = "bg-emerald-500/10 text-emerald-600 border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-400"
    icon = <ShieldCheck className="w-3.5 h-3.5" />
  } else if (status === 'rejected') {
    styles = "bg-red-500/10 text-red-600 border-red-500/20 dark:bg-red-500/10 dark:text-red-400"
    icon = <XOctagon className="w-3.5 h-3.5" />
  } else if (status === 'cancelled') {
    styles = "bg-blue-500/10 text-blue-600 border-blue-500/20 dark:bg-blue-500/10 dark:text-blue-400"
    icon = <AlertTriangle className="w-3.5 h-3.5" />
  } else if (status === 'expired') {
    styles = "bg-zinc-500/10 text-zinc-500 border-zinc-500/20 dark:bg-zinc-500/10 dark:text-zinc-400"
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold capitalize ${styles}`}>
      {icon}
      {status === 'cancelled' ? 'Alterações solicitadas' : status}
    </span>
  )
}

export default function AgentApprovals() {
  const queryClient = useQueryClient()
  const [selectedRequest, setSelectedRequest] = useState<ApprovalRequest | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [isDecisionModalOpen, setIsDecisionModalOpen] = useState(false)
  const [decisionType, setDecisionType] = useState<'approve' | 'reject' | 'request-changes' | null>(null)
  const [decisionReason, setDecisionReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Fetch approval requests
  const { data: requests = [], isLoading, isRefetching, refetch } = useQuery<ApprovalRequest[]>({
    queryKey: ['agent-approvals', statusFilter],
    queryFn: async () => {
      const res = await api.get('/admin/agent-approvals', {
        params: statusFilter ? { status: statusFilter } : {}
      })
      return res.data
    }
  })

  // Mutations for approvals
  const decisionMutation = useMutation({
    mutationFn: async ({ id, type, reason }: { id: string; type: 'approve' | 'reject' | 'request-changes'; reason: string }) => {
      const endpoint = `/admin/agent-approvals/${id}/${type}`
      const res = await api.post(endpoint, { decision_reason: reason })
      return res.data
    },
    onSuccess: (data) => {
      toast.success(`Solicitação ${data.status === 'approved' ? 'aprovada' : data.status === 'rejected' ? 'rejeitada' : 'alteração solicitada'} com sucesso!`)
      queryClient.invalidateQueries({ queryKey: ['agent-approvals'] })
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

  const openDecisionModal = (type: 'approve' | 'reject' | 'request-changes') => {
    setDecisionType(type)
    setIsDecisionModalOpen(true)
  }

  // Format date helper
  const formatDate = (isoString?: string) => {
    if (!isoString) return '-'
    try {
      const date = new Date(isoString)
      return date.toLocaleString('pt-BR')
    } catch {
      return isoString
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-foreground">
            Aprovações de Agentes (HITL)
          </h1>
          <p className="text-muted-foreground mt-1">
            Revise solicitações de aprovação pendentes antes de executar chamadas de ferramentas de alto risco.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isLoading || isRefetching}
          className="inline-flex items-center gap-2 self-start md:self-auto bg-card hover:bg-secondary text-foreground font-semibold px-4 py-2 border border-border rounded-xl shadow-sm transition-all duration-200 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${(isLoading || isRefetching) ? 'animate-spin' : ''}`} />
          {isRefetching ? 'Atualizando...' : 'Atualizar'}
        </button>
      </div>

      {/* Filter and Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left 2 Columns: Filters & Request List */}
        <div className="lg:col-span-2 space-y-4">
          
          {/* Filters Bar */}
          <div className="bg-card rounded-2xl border border-border p-4 shadow-sm flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 text-muted-foreground text-sm font-semibold shrink-0">
              <SlidersHorizontal className="w-4 h-4" />
              Filtrar por:
            </div>
            
            <div className="flex gap-2 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
              {[
                { label: 'Todos', value: '' },
                { label: 'Pendentes', value: 'pending' },
                { label: 'Aprovados', value: 'approved' },
                { label: 'Rejeitados', value: 'rejected' },
                { label: 'Alterações', value: 'cancelled' },
                { label: 'Expirados', value: 'expired' }
              ].map((filter) => (
                <button
                  key={filter.value}
                  onClick={() => {
                    setStatusFilter(filter.value)
                    setSelectedRequest(null)
                  }}
                  className={`
                    px-4 py-1.5 rounded-full text-xs font-bold transition-all border shrink-0
                    ${statusFilter === filter.value 
                      ? 'bg-primary border-primary text-primary-foreground shadow-sm' 
                      : 'bg-background hover:bg-secondary text-muted-foreground border-border'}
                  `}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>

          {/* List of Requests */}
          <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
            {isLoading ? (
              <div className="p-12 text-center text-muted-foreground flex flex-col items-center justify-center gap-3">
                <RefreshCw className="w-8 h-8 animate-spin text-primary" />
                <span className="font-semibold">Carregando solicitações de aprovação...</span>
              </div>
            ) : requests.length === 0 ? (
              <div className="p-12 text-center text-muted-foreground flex flex-col items-center justify-center gap-2">
                <ShieldCheck className="w-10 h-10 text-muted-foreground/60" />
                <h3 className="font-bold text-foreground mt-2">Nenhuma solicitação encontrada</h3>
                <p className="text-sm">Não há aprovações pendentes ou concluídas sob estes critérios.</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {requests.map((req) => {
                  const isSelected = selectedRequest?.id === req.id
                  return (
                    <div
                      key={req.id}
                      onClick={() => setSelectedRequest(req)}
                      className={`
                        p-5 cursor-pointer transition-all duration-200 flex items-start justify-between gap-4 hover:bg-secondary/40
                        ${isSelected ? 'bg-secondary/60 border-l-4 border-primary pl-4' : ''}
                      `}
                    >
                      <div className="space-y-1.5 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <RiskBadge risk={req.risk_level} />
                          <StatusBadge status={req.status} />
                        </div>
                        <h4 className="font-bold text-foreground text-sm md:text-base leading-tight truncate">
                          Run: <span className="font-mono text-xs text-muted-foreground">{req.agent_run_id}</span>
                        </h4>
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {req.reason}
                        </p>
                        <div className="text-[10px] text-muted-foreground font-semibold flex items-center gap-2">
                          <span>Por: {req.requested_by}</span>
                          <span>•</span>
                          <span>Criado: {formatDate(req.created_at)}</span>
                        </div>
                      </div>
                      
                      <div className="shrink-0 flex items-center self-center text-muted-foreground">
                        <ChevronRight className={`w-5 h-5 transition-transform duration-200 ${isSelected ? 'translate-x-1' : ''}`} />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Column: Detail Panel */}
        <div className="lg:col-span-1">
          {selectedRequest ? (
            <div className="bg-card border border-border rounded-2xl shadow-sm overflow-hidden sticky top-24 divide-y divide-border">
              
              {/* Detail Header */}
              <div className="p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-black text-foreground uppercase tracking-wider text-sm">
                    Detalhes da Solicitação
                  </h3>
                  <button 
                    onClick={() => setSelectedRequest(null)}
                    className="p-1 hover:bg-secondary rounded-lg text-muted-foreground transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                
                <div className="space-y-1.5">
                  <div className="flex gap-2">
                    <RiskBadge risk={selectedRequest.risk_level} />
                    <StatusBadge status={selectedRequest.status} />
                  </div>
                  <div className="text-xs text-muted-foreground font-semibold">
                    ID: <span className="font-mono">{selectedRequest.id}</span>
                  </div>
                </div>
              </div>

              {/* Info Body */}
              <div className="p-5 space-y-4 text-sm">
                
                {/* Reason & Workflow Details */}
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground font-black uppercase">Motivo / Gatilho</span>
                  <p className="text-foreground font-medium bg-secondary/30 p-3 rounded-xl border border-border">
                    {selectedRequest.reason}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <span className="text-[10px] text-muted-foreground font-black uppercase block">Reviewer Role</span>
                    <span className="font-bold text-foreground capitalize flex items-center gap-1 mt-0.5">
                      <User className="w-3.5 h-3.5 text-muted-foreground" />
                      {selectedRequest.reviewer_role.replace('admin_', '')}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground font-black uppercase block">Solicitado Por</span>
                    <span className="font-bold text-foreground mt-0.5 block truncate">
                      {selectedRequest.requested_by}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2 gap-3">
                  <div>
                    <span className="text-[10px] text-muted-foreground font-black uppercase block">Data de Criação</span>
                    <span className="text-xs font-semibold text-foreground mt-0.5 block">
                      {formatDate(selectedRequest.created_at)}
                    </span>
                  </div>
                  {selectedRequest.status === 'pending' ? (
                    <div>
                      <span className="text-[10px] text-muted-foreground font-black uppercase block">Expira Em</span>
                      <span className="text-xs font-semibold text-foreground mt-0.5 block flex items-center gap-1 text-orange-500">
                        <Clock className="w-3 h-3" />
                        {formatDate(selectedRequest.expires_at)}
                      </span>
                    </div>
                  ) : (
                    <div>
                      <span className="text-[10px] text-muted-foreground font-black uppercase block">Decidido Em</span>
                      <span className="text-xs font-semibold text-foreground mt-0.5 block">
                        {formatDate(selectedRequest.decided_at)}
                      </span>
                    </div>
                  )}
                </div>

                {/* Agent Run / Task ID */}
                <div className="space-y-1">
                  <span className="text-[10px] text-muted-foreground font-black uppercase block">ID da Execução (Run)</span>
                  <span className="font-mono text-xs text-foreground bg-secondary/50 px-2 py-1 rounded border border-border block select-all truncate">
                    {selectedRequest.agent_run_id}
                  </span>
                </div>

                {selectedRequest.task_id && (
                  <div>
                    <span className="text-[10px] text-muted-foreground font-black uppercase block">ID da Task</span>
                    <span className="font-mono text-xs text-foreground bg-secondary/50 px-2 py-1 rounded border border-border block truncate">
                      {selectedRequest.task_id}
                    </span>
                  </div>
                )}
              </div>

              {/* Sanitized Context Section */}
              {selectedRequest.sanitized_context && (
                <div className="p-5 space-y-2">
                  <span className="text-xs text-muted-foreground font-black uppercase flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5" />
                    Contexto Sanitizado (Ferramenta)
                  </span>
                  
                  <div className="bg-slate-950 text-slate-200 p-4 rounded-xl font-mono text-[11px] overflow-auto max-h-64 scrollbar-thin border border-slate-900 shadow-inner">
                    <pre className="whitespace-pre-wrap word-break-all">
                      {JSON.stringify(selectedRequest.sanitized_context, null, 2)}
                    </pre>
                  </div>
                  <p className="text-[10px] text-muted-foreground italic leading-normal">
                    * Parâmetros sensíveis (prompts, chaves) foram omitidos ou marcados como redigidos para segurança.
                  </p>
                </div>
              )}

              {/* Review History / Details */}
              {selectedRequest.status !== 'pending' && (
                <div className="p-5 bg-secondary/10 space-y-3">
                  <h4 className="font-black text-xs text-foreground uppercase tracking-wider">
                    Histórico da Decisão
                  </h4>
                  <div className="space-y-2 text-xs">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <span className="text-muted-foreground block text-[9px] uppercase font-bold">Decidido Por</span>
                        <span className="font-bold text-foreground">{selectedRequest.decided_by || '-'}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[9px] uppercase font-bold">Data da Decisão</span>
                        <span className="font-semibold text-foreground">{formatDate(selectedRequest.decided_at)}</span>
                      </div>
                    </div>
                    {selectedRequest.decision_reason && (
                      <div className="mt-1 bg-background/50 border border-border p-3 rounded-xl">
                        <span className="text-muted-foreground block text-[9px] uppercase font-bold mb-1">Comentários</span>
                        <p className="text-foreground leading-relaxed italic">
                          "{selectedRequest.decision_reason}"
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Review Actions Panel */}
              {selectedRequest.status === 'pending' && (
                <div className="p-5 bg-secondary/20 space-y-3">
                  <h4 className="font-black text-xs text-foreground uppercase tracking-wider">
                    Ações de Revisão
                  </h4>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <button
                      onClick={() => openDecisionModal('approve')}
                      className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-all text-xs border border-emerald-700 shadow-sm"
                    >
                      <Check className="w-3.5 h-3.5" />
                      Aprovar
                    </button>
                    <button
                      onClick={() => openDecisionModal('reject')}
                      className="w-full bg-red-600 hover:bg-red-500 text-white font-bold py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-all text-xs border border-red-700 shadow-sm"
                    >
                      <X className="w-3.5 h-3.5" />
                      Rejeitar
                    </button>
                    <button
                      onClick={() => openDecisionModal('request-changes')}
                      className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-all text-xs border border-blue-700 shadow-sm"
                    >
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Revisar
                    </button>
                  </div>
                </div>
              )}

            </div>
          ) : (
            <div className="bg-card border border-border border-dashed rounded-2xl p-8 text-center text-muted-foreground h-64 flex flex-col items-center justify-center gap-2 shadow-inner">
              <Eye className="w-8 h-8 text-muted-foreground/45" />
              <p className="font-semibold text-sm">Selecione uma solicitação</p>
              <p className="text-xs max-w-[200px] mx-auto">
                Clique em uma solicitação na lista para ver seus detalhes e realizar ações de auditoria ou aprovação.
              </p>
            </div>
          )}
        </div>

      </div>

      {/* Decision Modal */}
      {isDecisionModalOpen && selectedRequest && decisionType && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-3xl max-w-lg w-full overflow-hidden shadow-2xl p-6 space-y-4 animate-in zoom-in-95 duration-200">
            
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <h3 className="text-lg font-black text-foreground flex items-center gap-2">
                {decisionType === 'approve' ? (
                  <>
                    <div className="p-1.5 bg-emerald-500/10 text-emerald-500 rounded-lg">
                      <Check className="w-5 h-5" />
                    </div>
                    Confirmar Aprovação
                  </>
                ) : decisionType === 'reject' ? (
                  <>
                    <div className="p-1.5 bg-red-500/10 text-red-500 rounded-lg">
                      <X className="w-5 h-5" />
                    </div>
                    Confirmar Rejeição
                  </>
                ) : (
                  <>
                    <div className="p-1.5 bg-blue-500/10 text-blue-500 rounded-lg">
                      <AlertTriangle className="w-5 h-5" />
                    </div>
                    Solicitar Alterações
                  </>
                )}
              </h3>
              <button 
                onClick={() => {
                  setIsDecisionModalOpen(false)
                  setDecisionReason('')
                }}
                className="p-1.5 hover:bg-secondary rounded-lg text-muted-foreground transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-sm text-muted-foreground leading-relaxed">
              Você está prestes a{' '}
              <strong className="text-foreground">
                {decisionType === 'approve' ? 'APROVAR' : decisionType === 'reject' ? 'REJEITAR' : 'SOLICITAR ALTERAÇÕES para'}
              </strong>{' '}
              a execução do agente run{' '}
              <code className="bg-secondary/60 px-1 py-0.5 rounded font-mono text-xs text-foreground">
                {selectedRequest.agent_run_id.slice(0, 8)}...
              </code>
              {decisionType === 'approve' && ' e continuar seu fluxo de execução.'}
              {decisionType === 'reject' && ' e interromper a execução marcando-a como falha.'}
              {decisionType === 'request-changes' && ' e pausar a execução até novos comandos do usuário.'}
            </p>

            <form onSubmit={handleDecisionSubmit} className="space-y-4">
              <div className="space-y-2">
                <label 
                  htmlFor="decision-reason" 
                  className="block text-xs font-black uppercase text-muted-foreground"
                >
                  Motivo / Justificativa (Opcional)
                </label>
                <textarea
                  id="decision-reason"
                  rows={4}
                  className="w-full px-4 py-3 rounded-xl border border-border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all resize-none"
                  placeholder="Descreva o motivo desta decisão para fins de auditoria..."
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setIsDecisionModalOpen(false)
                    setDecisionReason('')
                  }}
                  className="px-5 py-2.5 rounded-xl border border-border hover:bg-secondary font-bold text-xs transition-all text-muted-foreground"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className={`
                    px-5 py-2.5 rounded-xl text-white font-bold text-xs transition-all shadow-md flex items-center gap-2
                    ${decisionType === 'approve' ? 'bg-emerald-600 hover:bg-emerald-500 border border-emerald-700' : ''}
                    ${decisionType === 'reject' ? 'bg-red-600 hover:bg-red-500 border border-red-700' : ''}
                    ${decisionType === 'request-changes' ? 'bg-blue-600 hover:bg-blue-500 border border-blue-700' : ''}
                    disabled:opacity-50
                  `}
                >
                  {isSubmitting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  {decisionType === 'approve' ? 'Aprovar Execução' : decisionType === 'reject' ? 'Rejeitar Execução' : 'Enviar Solicitação'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
