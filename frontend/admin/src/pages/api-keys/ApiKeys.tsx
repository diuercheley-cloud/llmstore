import { useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/card'
import { Badge } from '../../components/badge'
import { Button } from '../../components/button'
import api from '../../lib/api'
import { Key, Copy, Trash2, RotateCcw, Plus, UserRound } from 'lucide-react'
import { toast } from 'sonner'
import { APIError } from '../../lib/api'

interface ApiKey {
  id: string
  client_id: string
  client_name?: string
  plan_name?: string
  name: string
  key_prefix: string
  created_at: string
  expires_at: string | null
  last_used_at: string | null
  revoked_at: string | null
  is_active: boolean
}

interface ClientOption {
  id: string
  name: string
  billing_status?: string
}

function extractSecret(result: any): string | null {
  return result?.api_key?.api_key || result?.api_key || result?.key || null
}

export default function ApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [clients, setClients] = useState<ClientOption[]>([])
  const [loading, setLoading] = useState(true)
  const [rotatingId, setRotatingId] = useState<string | null>(null)
  const [newKey, setNewKey] = useState<string | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [createClientId, setCreateClientId] = useState('')
  const [createName, setCreateName] = useState('')

  const fetchKeys = async () => {
    try {
      const data = await api.listApiKeys()
      setKeys(data)
    } catch {
      toast.error('Falha ao carregar API keys')
    } finally {
      setLoading(false)
    }
  }

  const fetchClients = async () => {
    try {
      const data: any = await api.listClients()
      setClients(Array.isArray(data) ? data : data?.items || [])
    } catch {
      toast.error('Falha ao carregar clientes')
    }
  }

  useEffect(() => {
    fetchKeys()
    fetchClients()
  }, [])

  useEffect(() => {
    if (!createClientId && clients.length > 0) {
      setCreateClientId(clients[0].id)
    }
  }, [clients, createClientId])

  const handleCreate = async () => {
    try {
      if (!createClientId) {
        toast.error('Selecione um cliente')
        return
      }
      if (!createName.trim()) {
        toast.error('Informe o nome da chave')
        return
      }
      const result = await api.createApiKey({ client_id: createClientId, name: createName.trim() })
      const secret = extractSecret(result)
      setNewKey(secret)
      toast.success('Chave criada')
      setIsCreateOpen(false)
      setCreateName('')
      fetchKeys()
    } catch {
      toast.error('Falha ao criar chave')
    }
  }

  const handleRotate = async (id: string) => {
    const current = keys.find(key => key.id === id)
    if (current?.revoked_at) {
      toast.error('Chave revogada não pode ser rotacionada')
      return
    }

    try {
      setRotatingId(id)
      const result = await api.rotateApiKey(id)
      const secret = extractSecret(result)
      if (!secret) {
        throw new Error('Backend não retornou a nova chave')
      }
      setNewKey(secret)
      toast.success('Chave rotacionada')
      window.scrollTo({ top: 0, behavior: 'smooth' })
      await fetchKeys()
    } catch (error) {
      if (error instanceof APIError) {
        toast.error((error.data as any)?.detail || error.message || 'Falha ao rotacionar')
        return
      }
      toast.error(error instanceof Error ? error.message : 'Falha ao rotacionar')
    } finally {
      setRotatingId(null)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Excluir esta chave API?')) return
    try {
      await api.deleteApiKey(id)
      toast.success('Chave excluída')
      fetchKeys()
    } catch {
      toast.error('Falha ao excluir')
    }
  }

  const selectedClient = useMemo(
    () => clients.find(client => client.id === createClientId),
    [clients, createClientId],
  )

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">API Keys</h1>
          <p className="text-muted-foreground">Gerencie chaves de API para integrações</p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)}>
          <Plus className="w-4 h-4 mr-2" /> Nova Chave
        </Button>
      </div>

      {newKey && (
        <Card className="border-yellow-500/50 bg-yellow-500/5">
          <CardHeader>
            <CardTitle className="text-yellow-600">Chave gerada - copie agora!</CardTitle>
          </CardHeader>
          <CardContent>
            <code className="block p-3 bg-muted rounded text-sm break-all">{newKey}</code>
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={() => {
                navigator.clipboard.writeText(newKey)
                toast.success('Copiado')
              }}
            >
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
              <CardContent className="flex flex-col gap-4 p-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex items-center gap-3">
                  <Key className="w-5 h-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium text-foreground">{k.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {k.client_name || k.client_id} · {k.key_prefix}... | criada {new Date(k.created_at).toLocaleDateString()}
                    </p>
                    <p className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">
                      {k.plan_name || 'N/A'} · {k.revoked_at ? 'Revogada' : k.is_active ? 'Ativa' : 'Inativa'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={k.revoked_at ? 'destructive' : k.is_active ? 'default' : 'secondary'}>
                    {k.revoked_at ? 'Revogada' : k.is_active ? 'Ativa' : 'Inativa'}
                  </Badge>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => handleRotate(k.id)}
                    isLoading={rotatingId === k.id}
                    title={k.revoked_at ? 'Chave revogada' : 'Rotacionar'}
                    disabled={Boolean(k.revoked_at)}
                  >
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                  <Button variant="outline" size="icon" onClick={() => handleDelete(k.id)} title="Excluir">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
          {keys.length === 0 && <p className="text-muted-foreground text-center py-8">Nenhuma chave API cadastrada.</p>}
        </div>
      )}

      {isCreateOpen && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-foreground/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-3xl border border-border bg-card shadow-2xl">
            <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
              <div>
                <h2 className="text-xl font-black text-foreground">Nova Chave</h2>
                <p className="text-sm text-muted-foreground">Cria uma API key para um cliente existente.</p>
              </div>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="rounded-xl border border-border px-3 py-2 text-sm font-bold text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                Fechar
              </button>
            </div>

            <div className="space-y-4 px-6 py-5">
              <label className="space-y-2 block">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Cliente</span>
                <select
                  value={createClientId}
                  onChange={e => setCreateClientId(e.target.value)}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                >
                  <option value="">Selecione um cliente</option>
                  {clients.map(client => (
                    <option key={client.id} value={client.id}>
                      {client.name} {client.billing_status ? `· ${client.billing_status}` : ''}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-2 block">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Nome da chave</span>
                <input
                  value={createName}
                  onChange={e => setCreateName(e.target.value)}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
                  placeholder="Ex: integração backend"
                />
              </label>

              {selectedClient && (
                <div className="flex items-center gap-2 rounded-2xl border border-border bg-secondary/40 px-4 py-3 text-sm text-muted-foreground">
                  <UserRound className="h-4 w-4" />
                  {selectedClient.name}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleCreate} disabled={!createClientId || !createName.trim()}>
                Criar chave
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
