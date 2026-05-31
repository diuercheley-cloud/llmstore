import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui-card'
import { Button } from '../../components/ui-button'
import { FileText, Download, BarChart3 } from 'lucide-react'
import { toast } from 'sonner'

const reports = [
  { id: 'monthly', label: 'Relatório Mensal', description: 'Uso, faturamento e métricas de performance do mês', icon: BarChart3 },
  { id: 'usage', label: 'Relatório de Uso', description: 'Detalhamento de requests, tokens e modelos por cliente', icon: FileText },
  { id: 'security', label: 'Relatório de Segurança', description: 'Eventos de segurança, tentativas de acesso e auditoria', icon: FileText },
  { id: 'billing', label: 'Relatório de Faturamento', description: 'Faturas geradas, pagas e pendentes', icon: FileText },
]

export default function Reports() {
  const handleDownload = (reportId: string) => {
    toast.success(`Relatório ${reportId} solicitado. O download começará em breve.`)
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Relatórios</h1>
      <p className="text-muted-foreground">Exporte relatórios gerenciais da plataforma</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {reports.map(r => (
          <Card key={r.id}>
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <r.icon className="w-8 h-8 text-primary mt-1" />
                  <div>
                    <CardTitle className="text-lg">{r.label}</CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">{r.description}</p>
                  </div>
                </div>
                <Button variant="outline" size="sm" onClick={() => handleDownload(r.id)}>
                  <Download className="w-4 h-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
