import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui-card'
import { Badge } from '../../components/ui-badge'
import { Button } from '../../components/ui-button'
import api from '../../lib/api'
import { Key, Copy, Trash2, RotateCcw, Plus } from 'lucide-react'
import { toast } from 'sonner'

interface ApiKey {
  id: string
  label: string
  prefix: string
  created_at: string
  expires_at: string | null
  last_used_at: string | null
  enabled: boolean
}

export default function ApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [newKey, setNewKey] = useState<string | null>(null)

  const fetchKeys = async () => {
    try {
      const data = await api.listApiKeys()
      setKeys(data)
    } catch { /* empty */ }
    setLoading(false)
  }

  useEffect(() => { fetchKeys() }, [])

  const handleCreate = async () => {
    try {
      const label = prompt('Nome da chave:')
      if (!label) return
      const result = await api.createApiKey({ label })
      setNewKey(result.key || result.api_key)
      toast.success('Chave criada')
      fetchKeys()
    } catch { toast.error('Falha ao criar chave') }
  }

  const handleRotate = async (id: string) => {
    try {
      const result = await api.rotateApiKey(id)
      setNewKey(result.key || result.api_key)
      toast.success('Chave rotacionada')
      fetchKeys()
    } catch { toast.error('Falha ao rotacionar') }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Excluir esta chave API?')) return
    try {
      await api.deleteApiKey(id)
      toast.success('Chave excluída')
      fetchKeys()
    } catch { toast.error('Falha ao excluir') }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">API Keys</h1>
          <p className="text-muted-foreground">Gerencie chaves de API para integrações</p>
        </div>
        <Button onClick={handleCreate}>
          <Plus className="w-4 h-4 mr-2" /> Nova Chave
        </Button>
      </div>

      {newKey && (
        <Card className="border-yellow-500/50 bg-yellow-500/5">
          <CardHeader><CardTitle className="text-yellow-600">Chave gerada - copie agora!</CardTitle></CardHeader>
          <CardContent>
            <code className="block p-3 bg-muted rounded text-sm break-all">{newKey}</code>
            <Button variant="outline" size="sm" className="mt-2" onClick={() => { navigator.clipboard.writeText(newKey); toast.success('Copiado') }}>
              <Copy className="w-4 h-4 mr-2" /> Copiar
            </Button>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <p className="text-muted-foreground">Carregando...</p>
      ) : (
        <div className="space-y-3">
          {keys.map(k => (
            <Card key={k.id}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <Key className="w-5 h-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">{k.label}</p>
                    <p className="text-sm text-muted-foreground">{k.prefix}... | criada {new Date(k.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={k.enabled ? 'default' : 'secondary'}>{k.enabled ? 'Ativa' : 'Inativa'}</Badge>
                  <Button variant="outline" size="icon" onClick={() => handleRotate(k.id)} title="Rotacionar"><RotateCcw className="w-4 h-4" /></Button>
                  <Button variant="outline" size="icon" onClick={() => handleDelete(k.id)} title="Excluir"><Trash2 className="w-4 h-4" /></Button>
                </div>
              </CardContent>
            </Card>
          ))}
          {keys.length === 0 && <p className="text-muted-foreground text-center py-8">Nenhuma chave API cadastrada.</p>}
        </div>
      )}
    </div>
  )
}
