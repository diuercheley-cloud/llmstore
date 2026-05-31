import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/card'
import { Button } from '../../components/button'
import api from '../../lib/api'
import { FileText, FolderOpen, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

export default function Rag() {
  const [collections, setCollections] = useState<any[]>([])
  const [usage, setUsage] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      const [cols, u] = await Promise.all([
        api.listRagCollections().catch(() => []),
        api.getRagUsage().catch(() => null),
      ])
      setCollections(cols)
      setUsage(u)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [])

  const handleCreate = async () => {
    const name = prompt('Nome da coleção:')
    if (!name) return
    try {
      await api.createRagCollection({ name })
      toast.success('Coleção criada')
      fetchData()
    } catch { toast.error('Falha ao criar') }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">RAG</h1>
          <p className="text-muted-foreground">Retrieval-Augmented Generation - gerencie coleções e documentos</p>
        </div>
        <Button onClick={handleCreate}><Plus className="w-4 h-4 mr-2" /> Nova Coleção</Button>
      </div>

      {usage && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card><CardContent className="flex items-center gap-3 p-4"><FileText className="w-8 h-8 text-blue-500" /><div><p className="text-sm text-muted-foreground">Total de Documentos</p><p className="text-2xl font-bold">{usage.total_documents ?? 0}</p></div></CardContent></Card>
          <Card><CardContent className="flex items-center gap-3 p-4"><FolderOpen className="w-8 h-8 text-green-500" /><div><p className="text-sm text-muted-foreground">Coleções</p><p className="text-2xl font-bold">{collections.length}</p></div></CardContent></Card>
        </div>
      )}

      <Card><CardHeader><CardTitle>Coleções</CardTitle></CardHeader>
        <CardContent>
          {loading ? <p>Carregando...</p> : (
            <div className="space-y-3">
              {collections.map(c => (
                <Card key={c.id}><CardContent className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3"><FolderOpen className="w-5 h-5 text-muted-foreground" /><div><p className="font-medium">{c.name}</p><p className="text-sm text-muted-foreground">{c.document_count ?? 0} documentos</p></div></div>
                </CardContent></Card>
              ))}
              {collections.length === 0 && <p className="text-muted-foreground text-center py-8">Nenhuma coleção encontrada.</p>}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
