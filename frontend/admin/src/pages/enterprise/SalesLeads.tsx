import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Briefcase,
  Users,
  DollarSign,
  Plus,
  Trash2,
  TrendingUp,
  Calendar,
  Save,
  Calculator,
  Percent,
  CheckCircle2,
  MessageSquare,
  ChevronRight,
  Info,
  Clock,
} from 'lucide-react'
import { toast } from 'sonner'
import api from '../../lib/api'

type Lead = {
  id: string
  company_name: string
  contact_name: string
  contact_email: string
  contact_phone?: string | null
  segment: string
  source: string
  status: string
  estimated_value: number
  next_follow_up_at?: string | null
  notes?: string | null
  timeline_notes?: Array<{
    id: string
    content: string
    created_at: string
  }>
}

type QuotePreviewResult = {
  company_name: string
  plan: string
  currency: string
  totals: {
    setup: number
    recurring: number
    first_month_final: number
  }
}

export default function SalesLeads() {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [selectedLeadForNotes, setSelectedLeadForNotes] = useState<Lead | null>(null)
  const [newNoteContent, setNewNoteContent] = useState('')
  const [selectedLeadForAdvance, setSelectedLeadForAdvance] = useState<Lead | null>(null)
  const [newStage, setNewStage] = useState('')
  const [advanceNote, setAdvanceNote] = useState('')

  // Create Lead Form State
  const [leadForm, setLeadForm] = useState({
    company_name: '',
    contact_name: '',
    contact_email: '',
    contact_phone: '',
    segment: '',
    source: '',
    estimated_value: 0,
    next_follow_up_at: '',
    notes: '',
  })

  // Quote Simulator Form State
  const [quoteForm, setQuoteForm] = useState({
    company_name: '',
    plan: 'Basic',
    users: 5,
    models: 2,
    responses: 1000,
    support_hours: 2,
    custom_integration_hours: 10,
    discount_percent: 0,
    rag: false,
    tts: false,
    embeddings: false,
  })

  const [quoteResult, setQuoteResult] = useState<QuotePreviewResult | null>(null)

  // Queries
  const { data: leads, isLoading: isLoadingLeads } = useQuery<Lead[]>({
    queryKey: ['sales-leads', statusFilter],
    queryFn: async () => {
      return api.listLeads(statusFilter || undefined)
    },
  })

  // Mutations
  const createLeadMutation = useMutation({
    mutationFn: async (payload: any) => api.createLead(payload),
    onSuccess: () => {
      toast.success('Lead adicionado com sucesso!')
      setIsCreateOpen(false)
      setLeadForm({
        company_name: '',
        contact_name: '',
        contact_email: '',
        contact_phone: '',
        segment: '',
        source: '',
        estimated_value: 0,
        next_follow_up_at: '',
        notes: '',
      })
      queryClient.invalidateQueries({ queryKey: ['sales-leads'] })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Erro ao criar lead')
    },
  })

  const deleteLeadMutation = useMutation({
    mutationFn: async (id: string) => api.deleteLead(id),
    onSuccess: () => {
      toast.success('Lead removido com sucesso.')
      queryClient.invalidateQueries({ queryKey: ['sales-leads'] })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Erro ao deletar lead')
    },
  })

  const advanceStageMutation = useMutation({
    mutationFn: async ({ id, newStatus, note }: { id: string; newStatus: string; note?: string }) =>
      api.advanceLeadStage(id, newStatus, note),
    onSuccess: () => {
      toast.success('Estágio do lead atualizado.')
      setSelectedLeadForAdvance(null)
      setNewStage('')
      setAdvanceNote('')
      queryClient.invalidateQueries({ queryKey: ['sales-leads'] })
    },
    onError: (err: any) => {
      toast.error(err.message || 'Erro ao avançar estágio')
    },
  })

  const addNoteMutation = useMutation({
    mutationFn: async ({ id, content }: { id: string; content: string }) =>
      api.addLeadNote(id, content),
    onSuccess: () => {
      toast.success('Observação adicionada com sucesso.')
      setNewNoteContent('')
      queryClient.invalidateQueries({ queryKey: ['sales-leads'] })
      // Keep notes modal open but refresh selected lead detail
      if (selectedLeadForNotes) {
        const updatedLeads = queryClient.getQueryData<Lead[]>(['sales-leads', statusFilter])
        const updated = updatedLeads?.find(l => l.id === selectedLeadForNotes.id)
        if (updated) setSelectedLeadForNotes(updated)
      }
    },
    onError: (err: any) => {
      toast.error(err.message || 'Erro ao adicionar observação')
    },
  })

  const calculateQuoteMutation = useMutation({
    mutationFn: async (payload: any) => api.quotePreview(payload),
    onSuccess: (data: QuotePreviewResult) => {
      setQuoteResult(data)
      toast.success('Orçamento simulado com sucesso!')
    },
    onError: (err: any) => {
      toast.error(err.message || 'Erro ao simular orçamento')
    },
  })

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!leadForm.company_name || !leadForm.contact_name || !leadForm.contact_email) {
      toast.error('Preencha os campos obrigatórios: Empresa, Contato e Email.')
      return
    }
    const payload = {
      ...leadForm,
      next_follow_up_at: leadForm.next_follow_up_at ? new Date(leadForm.next_follow_up_at).toISOString() : null,
    }
    createLeadMutation.mutate(payload)
  }

  const handleDelete = (id: string, name: string) => {
    if (confirm(`Deseja realmente remover o lead da empresa "${name}"?`)) {
      deleteLeadMutation.mutate(id)
    }
  }

  const handleAdvanceSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedLeadForAdvance || !newStage) return
    advanceStageMutation.mutate({
      id: selectedLeadForAdvance.id,
      newStatus: newStage,
      note: advanceNote,
    })
  }

  const handleAddNoteSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedLeadForNotes || !newNoteContent.trim()) return
    addNoteMutation.mutate({
      id: selectedLeadForNotes.id,
      content: newNoteContent.trim(),
    })
  }

  const handleCalculateQuoteSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    calculateQuoteMutation.mutate(quoteForm)
  }

  const getStatusBadge = (status: string) => {
    const base = 'px-2 py-1 text-xs font-bold rounded-lg uppercase tracking-tighter '
    switch (status) {
      case 'won':
        return base + 'bg-emerald-500/15 text-emerald-500'
      case 'lost':
        return base + 'bg-rose-500/15 text-rose-500'
      case 'negotiation':
        return base + 'bg-amber-500/15 text-amber-500'
      case 'proposal_sent':
        return base + 'bg-indigo-500/15 text-indigo-500'
      case 'demo_scheduled':
        return base + 'bg-sky-500/15 text-sky-500'
      case 'contacted':
        return base + 'bg-blue-500/15 text-blue-500'
      case 'new':
      default:
        return base + 'bg-muted/30 text-muted-foreground'
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">
            Vendas & <span className="text-accent">CRM Leads</span>
          </h1>
          <p className="text-muted-foreground font-medium">
            Gerenciamento do funil de vendas, acompanhamento de leads e simulação de precificação comercial.
          </p>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="bg-accent text-background px-6 py-2.5 rounded-2xl font-bold text-sm flex items-center gap-2 hover:bg-accent/90 transition-colors self-start md:self-auto"
        >
          <Plus className="w-4 h-4" />
          Novo Lead
        </button>
      </header>

      {/* CRM Funnel Overview Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        {[
          { label: 'Total Leads', val: leads?.length || 0, color: 'text-foreground' },
          { label: 'Em Negociação', val: leads?.filter(l => l.status === 'negotiation' || l.status === 'proposal_sent').length || 0, color: 'text-amber-500' },
          { label: 'Ganhos (Won)', val: leads?.filter(l => l.status === 'won').length || 0, color: 'text-emerald-500' },
          { label: 'Perdidos (Lost)', val: leads?.filter(l => l.status === 'lost').length || 0, color: 'text-rose-500' },
          { label: 'Valor Estimado Total', val: `R$ ${(leads?.reduce((acc, l) => acc + (l.status !== 'lost' ? l.estimated_value : 0), 0) || 0).toLocaleString()}`, color: 'text-accent' }
        ].map((c, i) => (
          <div key={i} className="bg-card border border-border rounded-2xl p-5 shadow-sm">
            <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">{c.label}</span>
            <div className={`text-xl font-black mt-2 ${c.color}`}>{c.val}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Main Leads List */}
        <div className="xl:col-span-2 space-y-6">
          <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-black text-foreground">Funil de CRM</h2>
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                className="rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-accent"
              >
                <option value="">Todos os Estágios</option>
                <option value="new">New</option>
                <option value="contacted">Contacted</option>
                <option value="demo_scheduled">Demo Scheduled</option>
                <option value="proposal_sent">Proposal Sent</option>
                <option value="negotiation">Negotiation</option>
                <option value="won">Won</option>
                <option value="lost">Lost</option>
              </select>
            </div>

            {isLoadingLeads ? (
              <div className="py-12 text-center text-muted-foreground">Carregando leads...</div>
            ) : leads && leads.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs font-bold text-muted-foreground uppercase text-left">
                      <th className="pb-3">Empresa / Contato</th>
                      <th className="pb-3">Segmento</th>
                      <th className="pb-3">Status</th>
                      <th className="pb-3">Valor Estimado</th>
                      <th className="pb-3">Follow-up</th>
                      <th className="pb-3 text-right">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.map(l => (
                      <tr key={l.id} className="border-b border-border hover:bg-secondary/20 transition-colors">
                        <td className="py-4">
                          <div className="font-bold text-foreground">{l.company_name}</div>
                          <div className="text-xs text-muted-foreground">{l.contact_name} · {l.contact_email}</div>
                          {l.contact_phone && <div className="text-[10px] text-muted-foreground">{l.contact_phone}</div>}
                        </td>
                        <td className="py-4">
                          <span className="text-xs font-medium text-foreground">{l.segment}</span>
                          <div className="text-[10px] text-muted-foreground">Origem: {l.source}</div>
                        </td>
                        <td className="py-4">
                          <span className={getStatusBadge(l.status)}>{l.status.replace('_', ' ')}</span>
                        </td>
                        <td className="py-4 font-bold text-foreground">
                          R$ {l.estimated_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-4 text-xs text-muted-foreground">
                          {l.next_follow_up_at ? (
                            <span className="flex items-center gap-1.5">
                              <Calendar className="w-3.5 h-3.5" />
                              {new Date(l.next_follow_up_at).toLocaleDateString()}
                            </span>
                          ) : (
                            '-'
                          )}
                        </td>
                        <td className="py-4 text-right">
                          <div className="flex justify-end gap-1.5">
                            <button
                              title="Avançar Estágio"
                              onClick={() => {
                                setSelectedLeadForAdvance(l)
                                setNewStage(l.status)
                              }}
                              className="p-2 border border-border hover:bg-secondary text-foreground rounded-xl transition-colors"
                            >
                              <ChevronRight className="w-4 h-4" />
                            </button>
                            <button
                              title="Ver Observações"
                              onClick={() => setSelectedLeadForNotes(l)}
                              className="p-2 border border-border hover:bg-secondary text-foreground rounded-xl transition-colors relative"
                            >
                              <MessageSquare className="w-4 h-4" />
                              {l.timeline_notes && l.timeline_notes.length > 0 && (
                                <span className="absolute -top-1 -right-1 w-4 h-4 bg-accent text-[9px] font-black text-background rounded-full flex items-center justify-center">
                                  {l.timeline_notes.length}
                                </span>
                              )}
                            </button>
                            <button
                              title="Excluir"
                              onClick={() => handleDelete(l.id, l.company_name)}
                              className="p-2 border border-border hover:bg-rose-500/10 hover:border-rose-500 text-rose-500 rounded-xl transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-20 text-center border border-dashed border-border rounded-2xl bg-secondary/20">
                <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="font-bold text-foreground">Nenhum lead encontrado</h3>
                <p className="text-muted-foreground text-sm mt-1">Crie um novo lead para começar a acompanhar oportunidades.</p>
              </div>
            )}
          </div>
        </div>

        {/* Pricing & Quote Simulator */}
        <div className="space-y-6">
          <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
            <h2 className="text-lg font-black text-foreground mb-1 flex items-center gap-2">
              <Calculator className="w-5 h-5 text-accent" />
              Simulador de Orçamentos
            </h2>
            <p className="text-xs text-muted-foreground mb-6">
              Simule orçamentos comerciais usando regras do pricing e os scripts de geração locais do backend.
            </p>

            <form onSubmit={handleCalculateQuoteSubmit} className="space-y-4">
              <label className="block space-y-1.5">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Nome do Cliente</span>
                <input
                  type="text"
                  required
                  placeholder="Ex: Acme Enterprise"
                  value={quoteForm.company_name}
                  onChange={e => setQuoteForm({ ...quoteForm, company_name: e.target.value })}
                  className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm outline-none focus:border-accent"
                />
              </label>

              <div className="grid grid-cols-2 gap-4">
                <label className="block space-y-1.5">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Plano</span>
                  <select
                    value={quoteForm.plan}
                    onChange={e => setQuoteForm({ ...quoteForm, plan: e.target.value })}
                    className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm outline-none focus:border-accent"
                  >
                    <option value="Free">Free</option>
                    <option value="Basic">Basic</option>
                    <option value="Pro">Pro</option>
                    <option value="Enterprise Local">Enterprise Local</option>
                  </select>
                </label>

                <label className="block space-y-1.5">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Desconto (%)</span>
                  <div className="relative">
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={quoteForm.discount_percent}
                      onChange={e => setQuoteForm({ ...quoteForm, discount_percent: Number(e.target.value) })}
                      className="w-full rounded-xl border border-border bg-background pl-4 pr-8 py-2.5 text-sm outline-none focus:border-accent"
                    />
                    <Percent className="w-4 h-4 text-muted-foreground absolute right-3 top-3.5" />
                  </div>
                </label>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <label className="block space-y-1.5">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Usuários</span>
                  <input
                    type="number"
                    min="0"
                    value={quoteForm.users}
                    onChange={e => setQuoteForm({ ...quoteForm, users: Number(e.target.value) })}
                    className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm outline-none focus:border-accent"
                  />
                </label>

                <label className="block space-y-1.5">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Modelos Ativos</span>
                  <input
                    type="number"
                    min="1"
                    value={quoteForm.models}
                    onChange={e => setQuoteForm({ ...quoteForm, models: Number(e.target.value) })}
                    className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm outline-none focus:border-accent"
                  />
                </label>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <label className="block space-y-1.5">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Suporte (Horas)</span>
                  <input
                    type="number"
                    min="0"
                    value={quoteForm.support_hours}
                    onChange={e => setQuoteForm({ ...quoteForm, support_hours: Number(e.target.value) })}
                    className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm outline-none focus:border-accent"
                  />
                </label>

                <label className="block space-y-1.5">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Integração (Horas)</span>
                  <input
                    type="number"
                    min="0"
                    value={quoteForm.custom_integration_hours}
                    onChange={e => setQuoteForm({ ...quoteForm, custom_integration_hours: Number(e.target.value) })}
                    className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm outline-none focus:border-accent"
                  />
                </label>
              </div>

              {/* Addtional capabilities switches */}
              <div className="bg-secondary/20 border border-border rounded-2xl p-4 space-y-3">
                <div className="text-xs font-black uppercase tracking-widest text-muted-foreground mb-1">Tecnologias Adicionais</div>
                {[
                  { key: 'rag', label: 'Habilitar RAG Vault' },
                  { key: 'tts', label: 'Habilitar Pocket TTS' },
                  { key: 'embeddings', label: 'Habilitar Embeddings' }
                ].map(item => (
                  <label key={item.key} className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={(quoteForm as any)[item.key]}
                      onChange={e => setQuoteForm({ ...quoteForm, [item.key]: e.target.checked })}
                      className="rounded border-border text-accent focus:ring-accent outline-none"
                    />
                    <span className="text-sm font-medium text-foreground">{item.label}</span>
                  </label>
                ))}
              </div>

              <button
                type="submit"
                disabled={calculateQuoteMutation.isPending}
                className="w-full bg-accent text-background py-3 rounded-2xl font-bold hover:bg-accent/90 transition-all flex items-center justify-center gap-2"
              >
                <Calculator className="w-5 h-5" />
                {calculateQuoteMutation.isPending ? 'Calculando...' : 'Calcular Orçamento'}
              </button>
            </form>

            {/* Quote Result display */}
            {quoteResult ? (
              <div className="mt-6 border-t border-border pt-6 space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Cliente</span>
                  <span className="font-bold text-foreground">{quoteResult.company_name}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Plano Selecionado</span>
                  <span className="font-bold text-foreground text-sm bg-accent/15 text-accent px-2 py-0.5 rounded-lg">{quoteResult.plan}</span>
                </div>

                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-2xl p-4 space-y-2 mt-2">
                  <div className="flex justify-between text-xs text-emerald-600 font-medium">
                    <span>Taxa de Setup</span>
                    <span>{quoteResult.currency} {quoteResult.totals.setup.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between text-xs text-emerald-600 font-medium">
                    <span>Recorrência Mensal</span>
                    <span>{quoteResult.currency} {quoteResult.totals.recurring.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="border-t border-emerald-500/20 pt-2 flex justify-between font-black text-emerald-700 text-lg">
                    <span>Total 1º Mês</span>
                    <span>{quoteResult.currency} {quoteResult.totals.first_month_final.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  </div>
                </div>

                <div className="text-[10px] text-muted-foreground flex gap-1.5 items-start mt-2">
                  <Info className="w-4 h-4 shrink-0" />
                  <span>
                    Simulação local. Verifique os scripts do backend para regras customizadas de impostos, suporte premium ou quotas customizadas.
                  </span>
                </div>
              </div>
            ) : (
              <div className="mt-6 border border-dashed border-border rounded-2xl p-6 text-center text-xs text-muted-foreground">
                Insira os dados do cliente e clique em "Calcular Orçamento" para visualizar a estimativa.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* MODAL: Novo Lead */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-foreground/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-3xl border border-border bg-card shadow-2xl">
            <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
              <div>
                <h2 className="text-xl font-black text-foreground">Novo Lead Comercial</h2>
                <p className="text-sm text-muted-foreground">Adicione uma nova oportunidade ao pipeline de CRM.</p>
              </div>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="rounded-xl border border-border px-3 py-2 text-sm font-bold text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                Fechar
              </button>
            </div>

            <form onSubmit={handleCreateSubmit}>
              <div className="grid gap-4 px-6 py-5 md:grid-cols-2 max-h-[60vh] overflow-y-auto">
                <label className="space-y-1.5 block md:col-span-1">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Nome da Empresa *</span>
                  <input
                    required
                    value={leadForm.company_name}
                    onChange={e => setLeadForm({ ...leadForm, company_name: e.target.value })}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                    placeholder="Ex: Acme Corp"
                  />
                </label>

                <label className="space-y-1.5 block md:col-span-1">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Nome do Contato *</span>
                  <input
                    required
                    value={leadForm.contact_name}
                    onChange={e => setLeadForm({ ...leadForm, contact_name: e.target.value })}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                    placeholder="Nome da Pessoa"
                  />
                </label>

                <label className="space-y-1.5 block md:col-span-1">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Email de Contato *</span>
                  <input
                    required
                    type="email"
                    value={leadForm.contact_email}
                    onChange={e => setLeadForm({ ...leadForm, contact_email: e.target.value })}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                    placeholder="contato@empresa.com"
                  />
                </label>

                <label className="space-y-1.5 block md:col-span-1">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Telefone</span>
                  <input
                    value={leadForm.contact_phone}
                    onChange={e => setLeadForm({ ...leadForm, contact_phone: e.target.value })}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                    placeholder="Telefone ou WhatsApp"
                  />
                </label>

                <label className="space-y-1.5 block md:col-span-1">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Segmento</span>
                  <input
                    value={leadForm.segment}
                    onChange={e => setLeadForm({ ...leadForm, segment: e.target.value })}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                    placeholder="Ex: Health, Finance, Legal"
                  />
                </label>

                <label className="space-y-1.5 block md:col-span-1">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Origem</span>
                  <input
                    value={leadForm.source}
                    onChange={e => setLeadForm({ ...leadForm, source: e.target.value })}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                    placeholder="Ex: Website, Outbound, Indicação"
                  />
                </label>

                <label className="space-y-1.5 block md:col-span-1">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Valor Estimado (BRL)</span>
                  <input
                    type="number"
                    value={leadForm.estimated_value}
                    onChange={e => setLeadForm({ ...leadForm, estimated_value: Number(e.target.value) })}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                    placeholder="Ex: 50000"
                  />
                </label>

                <label className="space-y-1.5 block md:col-span-1">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Próximo Follow-up</span>
                  <input
                    type="date"
                    value={leadForm.next_follow_up_at}
                    onChange={e => setLeadForm({ ...leadForm, next_follow_up_at: e.target.value })}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent text-muted-foreground"
                  />
                </label>

                <label className="space-y-1.5 block md:col-span-2">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Notas Iniciais</span>
                  <textarea
                    value={leadForm.notes}
                    onChange={e => setLeadForm({ ...leadForm, notes: e.target.value })}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                    placeholder="Descreva detalhes da oportunidade, plano desejado ou observações adicionais..."
                    rows={3}
                  />
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="rounded-2xl border border-border px-4 py-2.5 text-sm font-bold text-muted-foreground hover:bg-secondary hover:text-foreground"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={createLeadMutation.isPending}
                  className="rounded-2xl bg-accent px-5 py-2.5 text-sm font-bold text-background hover:bg-accent/90 flex items-center gap-1.5"
                >
                  <Save className="w-4 h-4" />
                  {createLeadMutation.isPending ? 'Salvando...' : 'Salvar Lead'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Avançar Estágio */}
      {selectedLeadForAdvance && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-foreground/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-3xl border border-border bg-card shadow-2xl">
            <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
              <div>
                <h2 className="text-xl font-black text-foreground">Avançar Estágio</h2>
                <p className="text-sm text-muted-foreground">Atualize o status comercial da empresa "{selectedLeadForAdvance.company_name}".</p>
              </div>
              <button
                onClick={() => setSelectedLeadForAdvance(null)}
                className="rounded-xl border border-border px-3 py-2 text-sm font-bold text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                Fechar
              </button>
            </div>

            <form onSubmit={handleAdvanceSubmit}>
              <div className="px-6 py-5 space-y-4">
                <label className="block space-y-1.5">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Novo Estágio *</span>
                  <select
                    required
                    value={newStage}
                    onChange={e => setNewStage(e.target.value)}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                  >
                    <option value="new">New</option>
                    <option value="contacted">Contacted</option>
                    <option value="demo_scheduled">Demo Scheduled</option>
                    <option value="proposal_sent">Proposal Sent</option>
                    <option value="negotiation">Negotiation</option>
                    <option value="won">Won</option>
                    <option value="lost">Lost</option>
                  </select>
                </label>

                <label className="block space-y-1.5">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Observação do Histórico</span>
                  <textarea
                    value={advanceNote}
                    onChange={e => setAdvanceNote(e.target.value)}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                    placeholder="Ex: Ligação agendada, proposta aceita ou feedback do cliente..."
                    rows={3}
                  />
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
                <button
                  type="button"
                  onClick={() => setSelectedLeadForAdvance(null)}
                  className="rounded-2xl border border-border px-4 py-2.5 text-sm font-bold text-muted-foreground hover:bg-secondary hover:text-foreground"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={advanceStageMutation.isPending}
                  className="rounded-2xl bg-accent px-5 py-2.5 text-sm font-bold text-background hover:bg-accent/90"
                >
                  {advanceStageMutation.isPending ? 'Atualizando...' : 'Atualizar Estágio'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Observações (Histórico / Notas do Lead) */}
      {selectedLeadForNotes && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-foreground/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-3xl border border-border bg-card shadow-2xl">
            <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
              <div>
                <h2 className="text-xl font-black text-foreground">Histórico do Lead</h2>
                <p className="text-sm text-muted-foreground">Linha do tempo e observações da empresa "{selectedLeadForNotes.company_name}".</p>
              </div>
              <button
                onClick={() => setSelectedLeadForNotes(null)}
                className="rounded-xl border border-border px-3 py-2 text-sm font-bold text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                Fechar
              </button>
            </div>

            <div className="px-6 py-5 space-y-6 max-h-[50vh] overflow-y-auto">
              {/* Timeline list */}
              <div className="relative border-l border-border ml-2 pl-6 space-y-6">
                {selectedLeadForNotes.notes && (
                  <div className="relative">
                    <span className="absolute -left-[31px] top-1.5 w-3 h-3 bg-muted rounded-full border border-card" />
                    <div className="text-[10px] text-muted-foreground font-semibold flex items-center gap-1.5 mb-1">
                      <Clock className="w-3 h-3" />
                      Nota de Criação
                    </div>
                    <p className="text-sm text-foreground bg-secondary/30 p-3 rounded-xl border border-border font-medium">
                      {selectedLeadForNotes.notes}
                    </p>
                  </div>
                )}

                {selectedLeadForNotes.timeline_notes && selectedLeadForNotes.timeline_notes.length > 0 ? (
                  selectedLeadForNotes.timeline_notes.map(note => (
                    <div key={note.id} className="relative">
                      <span className="absolute -left-[31px] top-1.5 w-3 h-3 bg-accent rounded-full border border-card" />
                      <div className="text-[10px] text-muted-foreground font-semibold flex items-center gap-1.5 mb-1">
                        <Clock className="w-3 h-3" />
                        {new Date(note.created_at).toLocaleString()}
                      </div>
                      <p className="text-sm text-foreground bg-secondary/30 p-3 rounded-xl border border-border font-medium">
                        {note.content}
                      </p>
                    </div>
                  ))
                ) : (
                  !selectedLeadForNotes.notes && (
                    <div className="text-center py-6 text-sm text-muted-foreground">Nenhuma observação adicionada ainda.</div>
                  )
                )}
              </div>

              {/* Add Note Form */}
              <form onSubmit={handleAddNoteSubmit} className="border-t border-border pt-4">
                <label className="block space-y-2">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Nova Observação</span>
                  <textarea
                    required
                    value={newNoteContent}
                    onChange={e => setNewNoteContent(e.target.value)}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                    placeholder="Adicione observações sobre a ligação, emails ou propostas..."
                    rows={2}
                  />
                </label>
                <div className="flex justify-end mt-3">
                  <button
                    type="submit"
                    disabled={addNoteMutation.isPending}
                    className="rounded-2xl bg-accent px-5 py-2 text-sm font-bold text-background hover:bg-accent/90"
                  >
                    {addNoteMutation.isPending ? 'Adicionando...' : 'Adicionar Observação'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
