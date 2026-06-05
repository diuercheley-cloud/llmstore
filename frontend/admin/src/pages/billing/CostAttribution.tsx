import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/card'
import { Badge } from '../../components/badge'
import { Button } from '../../components/button'
import { Input } from '../../components/input'
import api from '../../lib/api'
import { 
  Calculator, 
  Download, 
  Filter, 
  Users, 
  Bot, 
  Wrench, 
  Layers 
} from 'lucide-react'

export default function CostAttribution() {
  const [summary, setSummary] = useState<any>(null)
  const [byAgent, setByAgent] = useState<any[]>([])
  const [byTool, setByTool] = useState<any[]>([])
  const [byTenant, setByTenant] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    tenant_id: '',
    start_date: '',
    end_date: ''
  })

  const fetchData = async () => {
    setLoading(true)
    try {
      const params = {
        tenant_id: filters.tenant_id || undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined
      }
      const [s, agents, tools, tenants] = await Promise.all([
        api.getCostsSummary(params),
        api.getCostsByAgent(params),
        api.getCostsByTool(params),
        api.getCostsByTenant()
      ])
      setSummary(s)
      setByAgent(agents)
      setByTool(tools)
      setByTenant(tenants)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      const res = await api.exportCosts({ ...filters, format })
      const blob = new Blob([res], { type: format === 'csv' ? 'text/csv' : 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `costs_export_${new Date().toISOString()}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed', err)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Atribuição de Custos</h1>
          <p className="text-muted-foreground">Rastreamento detalhado por tenant, agente e ferramenta</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => handleExport('csv')}>
            <Download className="w-4 h-4 mr-2" /> Exportar CSV
          </Button>
          <Button variant="outline" onClick={() => handleExport('json')}>
            <Download className="w-4 h-4 mr-2" /> Exportar JSON
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-4 flex flex-wrap gap-4 items-end">
          <div className="space-y-1">
            <label className="text-xs font-medium">Tenant ID</label>
            <Input 
              placeholder="Filtre por tenant..." 
              value={filters.tenant_id} 
              onChange={e => setFilters({...filters, tenant_id: e.target.value})}
              className="w-48"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium">Início</label>
            <Input 
              type="date"
              value={filters.start_date} 
              onChange={e => setFilters({...filters, start_date: e.target.value})}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium">Fim</label>
            <Input 
              type="date"
              value={filters.end_date} 
              onChange={e => setFilters({...filters, end_date: e.target.value})}
            />
          </div>
          <Button onClick={fetchData}>
            <Filter className="w-4 h-4 mr-2" /> Aplicar Filtros
          </Button>
        </CardContent>
      </Card>

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <Calculator className="w-8 h-8 text-green-500" />
              <div>
                <p className="text-sm text-muted-foreground">Custo Estimado Total</p>
                <p className="text-2xl font-bold">R$ {summary.total_cost.toFixed(4)}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <Layers className="w-8 h-8 text-blue-500" />
              <div>
                <p className="text-sm text-muted-foreground">Total de Eventos</p>
                <p className="text-2xl font-bold">{summary.event_count}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <Bot className="w-8 h-8 text-purple-500" />
              <div>
                <p className="text-sm text-muted-foreground">Agentes Ativos</p>
                <p className="text-2xl font-bold">{byAgent.length}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <Wrench className="w-8 h-8 text-orange-500" />
              <div>
                <p className="text-sm text-muted-foreground">Ferramentas Usadas</p>
                <p className="text-2xl font-bold">{byTool.length}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Bot className="w-5 h-5" /> Custos por Agente
            </CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground border-b">
                  <th className="pb-2">Agente ID</th>
                  <th className="pb-2">Eventos</th>
                  <th className="pb-2 text-right">Custo (BRL)</th>
                </tr>
              </thead>
              <tbody>
                {byAgent.map((a, idx) => (
                  <tr key={idx} className="border-t hover:bg-muted/50">
                    <td className="py-2 font-mono text-xs">{a.agent_id || 'N/A'}</td>
                    <td className="py-2">{a.event_count}</td>
                    <td className="py-2 text-right font-medium">R$ {a.total_cost.toFixed(4)}</td>
                  </tr>
                ))}
                {byAgent.length === 0 && (
                  <tr><td colSpan={3} className="py-4 text-center text-muted-foreground">Nenhum dado.</td></tr>
                )}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Wrench className="w-5 h-5" /> Custos por Ferramenta
            </CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground border-b">
                  <th className="pb-2">Ferramenta</th>
                  <th className="pb-2">Chamadas</th>
                  <th className="pb-2 text-right">Custo (BRL)</th>
                </tr>
              </thead>
              <tbody>
                {byTool.map((t, idx) => (
                  <tr key={idx} className="border-t hover:bg-muted/50">
                    <td className="py-2"><Badge variant="outline">{t.tool_name}</Badge></td>
                    <td className="py-2">{t.event_count}</td>
                    <td className="py-2 text-right font-medium">R$ {t.total_cost.toFixed(4)}</td>
                  </tr>
                ))}
                {byTool.length === 0 && (
                  <tr><td colSpan={3} className="py-4 text-center text-muted-foreground">Nenhum dado.</td></tr>
                )}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Users className="w-5 h-5" /> Distribuição por Tenant
            </CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground border-b">
                  <th className="pb-2">Tenant</th>
                  <th className="pb-2">Eventos</th>
                  <th className="pb-2 text-right">Custo Acumulado (BRL)</th>
                </tr>
              </thead>
              <tbody>
                {byTenant.map((t, idx) => (
                  <tr key={idx} className="border-t hover:bg-muted/50">
                    <td className="py-2 font-medium">{t.tenant_id}</td>
                    <td className="py-2">{t.event_count}</td>
                    <td className="py-2 text-right font-bold text-green-600">R$ {t.total_cost.toFixed(2)}</td>
                  </tr>
                ))}
                {byTenant.length === 0 && (
                  <tr><td colSpan={3} className="py-4 text-center text-muted-foreground">Nenhum dado.</td></tr>
                )}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
