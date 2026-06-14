import { useMemo, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CreditCard, DollarSign, FileText, Layers3, PlayCircle, RefreshCw, Wallet } from 'lucide-react'
import { toast } from 'sonner'

import api from '../../lib/api'

type BillingTab = 'overview' | 'plans' | 'pricing' | 'invoices' | 'payments'

function formatTokenLimit(value: number | null | undefined) {
  return value && value > 0 ? value.toLocaleString() : 'Ilimitado'
}

export default function Billing() {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<BillingTab>('overview')

  const { data: revenueSummary } = useQuery({
    queryKey: ['billing-revenue-summary'],
    queryFn: () => api.getRevenueSummary(),
  })

  const { data: invoicePreview } = useQuery({
    queryKey: ['billing-invoice-preview'],
    queryFn: () => api.previewInvoices(),
  })

  const { data: plans = [] } = useQuery({
    queryKey: ['billing-plans-admin'],
    queryFn: () => api.listBillingPlansAdmin(),
  })

  const { data: pricingRules = [] } = useQuery({
    queryKey: ['billing-pricing-rules'],
    queryFn: () => api.listPricingRules(),
  })

  const { data: invoices = [] } = useQuery({
    queryKey: ['billing-invoices'],
    queryFn: () => api.listInvoices(),
  })

  const { data: payments = [] } = useQuery({
    queryKey: ['billing-payments'],
    queryFn: () => api.listPayments(),
  })

  const generateInvoicesMutation = useMutation({
    mutationFn: () => api.generateInvoices({ due_in_days: 7, payment_method: 'manual', payment_instructions: 'Emitido pelo dashboard administrativo.' }),
    onSuccess: () => {
      toast.success('Geracao de faturas concluida.')
      invalidateBilling(queryClient)
    },
    onError: (error: any) => toast.error(error?.message || 'Falha ao gerar faturas'),
  })

  const runCycleMutation = useMutation({
    mutationFn: () => api.runBillingCycle(),
    onSuccess: () => {
      toast.success('Ciclo de billing executado.')
      invalidateBilling(queryClient)
    },
    onError: (error: any) => toast.error(error?.message || 'Falha ao executar ciclo'),
  })

  const monthlyRevenue = Number(revenueSummary?.monthly_revenue || 0)
  const totalRevenue = Number(revenueSummary?.total_revenue || 0)
  const pendingInvoices = Number(revenueSummary?.pending_invoices || 0)
  const previewClients = Array.isArray(invoicePreview?.clients) ? invoicePreview.clients : []

  const tabs: Array<{ id: BillingTab; label: string }> = useMemo(() => ([
    { id: 'overview', label: 'Overview' },
    { id: 'plans', label: 'Plans' },
    { id: 'pricing', label: 'Pricing Rules' },
    { id: 'invoices', label: 'Invoices' },
    { id: 'payments', label: 'Payments' },
  ]), [])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">Billing</h1>
          <p className="text-sm md:text-lg text-muted-foreground">Dashboard administrativo de receita, planos, precificacao, faturas e pagamentos.</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={() => invalidateBilling(queryClient)}
            className="rounded-xl border border-border px-4 py-2.5 text-sm font-bold text-foreground hover:bg-secondary"
          >
            Atualizar
          </button>
          <button
            type="button"
            onClick={() => generateInvoicesMutation.mutate()}
            disabled={generateInvoicesMutation.isPending}
            className="rounded-xl border border-border px-4 py-2.5 text-sm font-bold text-foreground hover:bg-secondary disabled:opacity-50"
          >
            {generateInvoicesMutation.isPending ? 'Gerando...' : 'Gerar Faturas'}
          </button>
          <button
            type="button"
            onClick={() => runCycleMutation.mutate()}
            disabled={runCycleMutation.isPending}
            className="flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white shadow-lg shadow-primary/20 hover:bg-primary/90 disabled:opacity-50"
          >
            <PlayCircle className="h-4 w-4" />
            {runCycleMutation.isPending ? 'Executando...' : 'Run Cycle'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Receita Total" value={`R$ ${totalRevenue.toFixed(2)}`} icon={<DollarSign className="h-5 w-5 text-emerald-500" />} />
        <MetricCard label="Mes Atual" value={`R$ ${monthlyRevenue.toFixed(2)}`} icon={<Wallet className="h-5 w-5 text-primary" />} />
        <MetricCard label="Pendentes" value={String(pendingInvoices)} icon={<FileText className="h-5 w-5" />} />
        <MetricCard label="Planos" value={String(plans.length)} icon={<Layers3 className="h-5 w-5" />} />
      </div>

      <div className="flex flex-wrap gap-2">
        {tabs.map(item => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`rounded-full px-4 py-2 text-xs font-black uppercase tracking-wider transition-all ${
              tab === item.id ? 'bg-primary text-white' : 'bg-secondary text-muted-foreground hover:text-foreground'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
          <section className="rounded-3xl border border-border bg-card p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-2 text-lg font-black text-foreground">
              <RefreshCw className="h-5 w-5 text-primary" />
              Preview de Faturas
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs font-black uppercase tracking-widest text-muted-foreground">
                    <th className="py-3 pr-4">Cliente</th>
                    <th className="py-3 pr-4">Plano</th>
                    <th className="py-3 pr-4">Preview</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {previewClients.map((item: any) => (
                    <tr key={item.client_id}>
                      <td className="py-3 pr-4 font-semibold text-foreground">{item.name}</td>
                      <td className="py-3 pr-4 text-muted-foreground">{item.billing_plan_code}</td>
                      <td className="py-3 pr-4 text-xs font-mono text-foreground">{JSON.stringify(item.invoice_preview)}</td>
                    </tr>
                  ))}
                  {previewClients.length === 0 && (
                    <tr>
                      <td colSpan={3} className="py-8 text-center text-muted-foreground">Nenhum preview disponivel.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="rounded-3xl border border-border bg-card p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-2 text-lg font-black text-foreground">
              <CreditCard className="h-5 w-5 text-primary" />
              Resumo
            </div>
            <div className="space-y-4">
              <SummaryRow label="Receita total" value={`R$ ${totalRevenue.toFixed(2)}`} />
              <SummaryRow label="Receita mensal" value={`R$ ${monthlyRevenue.toFixed(2)}`} />
              <SummaryRow label="Faturas pendentes" value={String(pendingInvoices)} />
              <SummaryRow label="Payments registrados" value={String(payments.length)} />
              <SummaryRow label="Invoices registradas" value={String(invoices.length)} />
            </div>
          </section>
        </div>
      )}

      {tab === 'plans' && (
        <DataCard title="Billing Plans">
          <SimpleTable
            headers={['Code', 'Nome', 'Limite RPM', 'Tokens/Dia', 'Modelos']}
            rows={plans.map((plan: any) => [
              plan.code,
              plan.name || '-',
              String(plan.rate_limit_per_minute ?? '-'),
              formatTokenLimit(plan.daily_token_quota),
              Array.isArray(plan.allowed_models) ? plan.allowed_models.join(', ') : plan.allowed_models_json || '-',
            ])}
            emptyLabel="Nenhum plano encontrado."
          />
        </DataCard>
      )}

      {tab === 'pricing' && (
        <DataCard title="Pricing Rules">
          <SimpleTable
            headers={['Billing Plan', 'Currency', 'Monthly', 'Overage / 1k', 'Ativa']}
            rows={pricingRules.map((rule: any) => [
              String(rule.billing_plan_id),
              rule.currency,
              String(rule.monthly_price),
              String(rule.overage_price_per_1k_tokens),
              rule.is_active ? 'sim' : 'nao',
            ])}
            emptyLabel="Nenhuma regra de preco encontrada."
          />
        </DataCard>
      )}

      {tab === 'invoices' && (
        <DataCard title="Invoices">
          <SimpleTable
            headers={['ID', 'Client', 'Amount', 'Status', 'Due Date']}
            rows={invoices.map((invoice: any) => [
              String(invoice.id).slice(0, 12),
              invoice.client_id || '-',
              String(invoice.amount ?? invoice.total_amount ?? '-'),
              invoice.status || '-',
              invoice.due_date ? new Date(invoice.due_date).toLocaleDateString() : '-',
            ])}
            emptyLabel="Nenhuma fatura encontrada."
          />
        </DataCard>
      )}

      {tab === 'payments' && (
        <DataCard title="Payments">
          <SimpleTable
            headers={['ID', 'Invoice', 'Amount', 'Status', 'Metodo']}
            rows={payments.map((payment: any) => [
              String(payment.id).slice(0, 12),
              payment.invoice_id || '-',
              String(payment.amount ?? '-'),
              payment.status || '-',
              payment.payment_method || '-',
            ])}
            emptyLabel="Nenhum pagamento encontrado."
          />
        </DataCard>
      )}
    </div>
  )
}

function invalidateBilling(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ['billing-revenue-summary'] })
  queryClient.invalidateQueries({ queryKey: ['billing-invoice-preview'] })
  queryClient.invalidateQueries({ queryKey: ['billing-plans-admin'] })
  queryClient.invalidateQueries({ queryKey: ['billing-pricing-rules'] })
  queryClient.invalidateQueries({ queryKey: ['billing-invoices'] })
  queryClient.invalidateQueries({ queryKey: ['billing-payments'] })
}

function MetricCard({ label, value, icon }: { label: string; value: string; icon: ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="mb-2 flex items-center gap-3 text-muted-foreground">{icon}</div>
      <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="text-2xl font-black text-foreground">{value}</div>
    </div>
  )
}

function DataCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-3xl border border-border bg-card p-5 shadow-sm">
      <div className="mb-4 text-lg font-black text-foreground">{title}</div>
      {children}
    </section>
  )
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-border bg-background px-4 py-3">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-black text-foreground">{value}</span>
    </div>
  )
}

function SimpleTable({ headers, rows, emptyLabel }: { headers: string[]; rows: string[][]; emptyLabel: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs font-black uppercase tracking-widest text-muted-foreground">
            {headers.map(header => (
              <th key={header} className="py-3 pr-4">{header}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((value, cellIndex) => (
                <td key={cellIndex} className="py-3 pr-4 text-foreground">{value}</td>
              ))}
            </tr>
          ))}
          {!rows.length && (
            <tr>
              <td colSpan={headers.length} className="py-8 text-center text-muted-foreground">{emptyLabel}</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
