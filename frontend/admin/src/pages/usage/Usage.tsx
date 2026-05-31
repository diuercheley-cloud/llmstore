import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/card'
import api from '../../lib/api'
import { TrendingUp, Server, Database, Activity } from 'lucide-react'

export default function Usage() {
  const [usage, setUsage] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getUsageSummary().then(setUsage).catch(() => {}).finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Uso</h1>
      <p className="text-muted-foreground">Métricas de uso da plataforma</p>

      {loading ? <p>Carregando...</p> : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card><CardContent className="flex items-center gap-3 p-4"><Activity className="w-8 h-8 text-blue-500" /><div><p className="text-sm text-muted-foreground">Requests</p><p className="text-2xl font-bold">{usage?.total_requests ?? 0}</p></div></CardContent></Card>
          <Card><CardContent className="flex items-center gap-3 p-4"><Server className="w-8 h-8 text-green-500" /><div><p className="text-sm text-muted-foreground">Modelos Ativos</p><p className="text-2xl font-bold">{usage?.active_models ?? 0}</p></div></CardContent></Card>
          <Card><CardContent className="flex items-center gap-3 p-4"><Database className="w-8 h-8 text-purple-500" /><div><p className="text-sm text-muted-foreground">Tokens Processados</p><p className="text-2xl font-bold">{(usage?.total_tokens ?? 0).toLocaleString()}</p></div></CardContent></Card>
          <Card><CardContent className="flex items-center gap-3 p-4"><TrendingUp className="w-8 h-8 text-orange-500" /><div><p className="text-sm text-muted-foreground">Clientes</p><p className="text-2xl font-bold">{usage?.total_clients ?? 0}</p></div></CardContent></Card>
        </div>
      )}
    </div>
  )
}
