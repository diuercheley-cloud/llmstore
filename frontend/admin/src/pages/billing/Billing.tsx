import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui-card'
import { Badge } from '../../components/ui-badge'
import api from '../../lib/api'
import { Wallet, CreditCard, TrendingUp, DollarSign } from 'lucide-react'

interface Invoice { id: string; client_id: string; amount: number; status: string; due_date: string; created_at: string }

export default function Billing() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.listInvoices().then(setInvoices).catch(() => {}),
      api.getRevenueSummary().then(setSummary).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Faturamento</h1>
      <p className="text-muted-foreground">Visualize faturas, pagamentos e receitas</p>

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card><CardContent className="flex items-center gap-3 p-4"><DollarSign className="w-8 h-8 text-green-500" /><div><p className="text-sm text-muted-foreground">Receita Total</p><p className="text-2xl font-bold">R$ {summary.total_revenue?.toFixed(2) ?? '0.00'}</p></div></CardContent></Card>
          <Card><CardContent className="flex items-center gap-3 p-4"><TrendingUp className="w-8 h-8 text-blue-500" /><div><p className="text-sm text-muted-foreground">Este Mês</p><p className="text-2xl font-bold">R$ {summary.monthly_revenue?.toFixed(2) ?? '0.00'}</p></div></CardContent></Card>
          <Card><CardContent className="flex items-center gap-3 p-4"><CreditCard className="w-8 h-8 text-purple-500" /><div><p className="text-sm text-muted-foreground">Pendente</p><p className="text-2xl font-bold">{summary.pending_invoices ?? 0}</p></div></CardContent></Card>
        </div>
      )}

      <Card><CardHeader><CardTitle className="flex items-center gap-2"><Wallet className="w-5 h-5" /> Faturas</CardTitle></CardHeader>
        <CardContent>
          {loading ? <p>Carregando...</p> : (
            <table className="w-full text-sm"><thead><tr className="text-left text-muted-foreground"><th className="pb-2">ID</th><th className="pb-2">Valor</th><th className="pb-2">Status</th><th className="pb-2">Vencimento</th></tr></thead>
              <tbody>{invoices.map(i => (
                <tr key={i.id} className="border-t"><td className="py-2 font-mono text-xs">{i.id.slice(0, 12)}...</td><td className="py-2">R$ {i.amount.toFixed(2)}</td><td className="py-2"><Badge variant={i.status === 'paid' ? 'default' : i.status === 'overdue' ? 'destructive' : 'secondary'}>{i.status}</Badge></td><td className="py-2">{new Date(i.due_date).toLocaleDateString()}</td></tr>
              ))}{invoices.length === 0 && <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">Nenhuma fatura encontrada.</td></tr>}</tbody></table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
