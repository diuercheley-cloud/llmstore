import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui-card'
import { Badge } from '../../components/ui-badge'
import api from '../../lib/api'
import { Shield, AlertTriangle, Lock, Users } from 'lucide-react'

export default function Security() {
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listSecurityEvents().then(setEvents).catch(() => {}).finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Segurança</h1>
      <p className="text-muted-foreground">Eventos de segurança e auditoria da plataforma</p>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card><CardContent className="flex items-center gap-3 p-4"><Shield className="w-8 h-8 text-green-500" /><div><p className="text-sm text-muted-foreground">Eventos Hoje</p><p className="text-2xl font-bold">{events.filter(e => new Date(e.created_at).toDateString() === new Date().toDateString()).length}</p></div></CardContent></Card>
        <Card><CardContent className="flex items-center gap-3 p-4"><AlertTriangle className="w-8 h-8 text-red-500" /><div><p className="text-sm text-muted-foreground">Alertas</p><p className="text-2xl font-bold">{events.filter(e => e.severity === 'high' || e.severity === 'critical').length}</p></div></CardContent></Card>
        <Card><CardContent className="flex items-center gap-3 p-4"><Lock className="w-8 h-8 text-blue-500" /><div><p className="text-sm text-muted-foreground">Bloqueios</p><p className="text-2xl font-bold">{events.filter(e => e.event_type === 'block').length}</p></div></CardContent></Card>
        <Card><CardContent className="flex items-center gap-3 p-4"><Users className="w-8 h-8 text-purple-500" /><div><p className="text-sm text-muted-foreground">Usuários Afetados</p><p className="text-2xl font-bold">{new Set(events.map(e => e.client_id || e.user_id)).size}</p></div></CardContent></Card>
      </div>

      <Card><CardHeader><CardTitle>Eventos Recentes</CardTitle></CardHeader>
        <CardContent>
          {loading ? <p>Carregando...</p> : (
            <table className="w-full text-sm"><thead><tr className="text-left text-muted-foreground"><th className="pb-2">Tipo</th><th className="pb-2">Severidade</th><th className="pb-2">Detalhe</th><th className="pb-2">Data</th></tr></thead>
              <tbody>{events.slice(0, 50).map(e => (
                <tr key={e.id} className="border-t"><td className="py-2 font-mono text-xs">{e.event_type}</td><td className="py-2"><Badge variant={e.severity === 'critical' || e.severity === 'high' ? 'destructive' : 'secondary'}>{e.severity}</Badge></td><td className="py-2 text-muted-foreground">{e.description || '-'}</td><td className="py-2 text-xs text-muted-foreground">{new Date(e.created_at).toLocaleString()}</td></tr>
              ))}{events.length === 0 && <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">Nenhum evento de segurança registrado.</td></tr>}</tbody></table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
