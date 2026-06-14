import { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, RefreshCw, Loader2 } from 'lucide-react';
import { api } from '../lib/api';
import { toast } from 'sonner';

export const ApiKeys = () => {
  const [keys, setKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);

  const loadKeys = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.listPortalApiKeys();
      setKeys(list);
    } catch (err) {
      console.error('Failed to load API keys', err);
      toast.error("Erro ao carregar chaves de API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadKeys();
  }, [loadKeys]);

  const handleCreate = async () => {
    const name = prompt("Nome da chave:");
    if (!name) return;

    setCreating(true);
    try {
      const newKey = await api.createPortalApiKey(name);
      toast.success("Chave criada com sucesso!", {
        description: `Sua chave é: ${newKey.api_key}. Guarde-a em um lugar seguro ela não será exibida novamente.`
      });
      loadKeys();
    } catch (err) {
      toast.error("Falha ao criar chave.");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Tem certeza que deseja revogar esta chave?")) return;
    try {
      await api.deletePortalApiKey(id);
      toast.success("Chave revogada.");
      loadKeys();
    } catch (err) {
      toast.error("Falha ao revogar chave.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">API Keys</h1>
        <button 
          onClick={handleCreate}
          disabled={creating}
          className="btn btn-primary w-full sm:w-auto"
        >
          {creating ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />}
          Create New Key
        </button>
      </div>

      <div className="card !p-0 overflow-hidden">
        {loading && !keys.length ? (
          <div className="p-12 flex flex-col items-center justify-center gap-4">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
            <p className="text-slate-500">Carregando chaves...</p>
          </div>
        ) : (
          <div className="resp-table-container">
            <table className="resp-table">
              <thead>
                <tr>
                  <th>NAME</th>
                  <th>KEY PREFIX</th>
                  <th>CREATED</th>
                  <th>LAST USED</th>
                  <th className="text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {keys.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-12 text-slate-400 italic">
                      Nenhuma chave encontrada.
                    </td>
                  </tr>
                ) : keys.map(k => (
                  <tr key={k.id}>
                    <td data-label="NAME" className="font-medium text-slate-900">{k.name}</td>
                    <td data-label="KEY PREFIX"><code className="bg-slate-100 px-2 py-1 rounded text-primary font-mono text-xs">{k.key_prefix || 'sk-***'}</code></td>
                    <td data-label="CREATED" className="text-slate-500">{k.created_at ? new Date(k.created_at).toLocaleDateString() : 'N/A'}</td>
                    <td data-label="LAST USED" className="text-slate-500">{k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}</td>
                    <td data-label="ACTIONS" className="md:text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button className="btn btn-outline !p-2" title="Rotate Key" disabled><RefreshCw size={16} /></button>
                        <button 
                          onClick={() => handleDelete(k.id)}
                          className="btn btn-danger !p-2" 
                          title="Revoke"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
