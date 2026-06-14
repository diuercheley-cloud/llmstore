import { useEffect, useState } from 'react';
import { Plus, Loader2, Webhook as WebhookIcon } from 'lucide-react';
import { api } from '../lib/api';
import { toast } from 'sonner';

export const Webhooks = () => {
  const [agents, setAgents] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedAgentId, setSelectedAgentId] = useState('');
  const [url, setUrl] = useState('');
  const [loadingAgents, setLoadingAgents] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [registration, setRegistration] = useState<{ webhook_id: string; secret: string } | null>(null);

  useEffect(() => {
    let mounted = true;
    const loadAgents = async () => {
      try {
        const items = await api.listAgents();
        if (!mounted) return;
        setAgents(items.map(agent => ({ id: agent.id, name: agent.name })));
        setSelectedAgentId(items[0]?.id || '');
      } catch (error) {
        toast.error('Falha ao carregar agentes para registrar webhook.');
      } finally {
        if (mounted) {
          setLoadingAgents(false);
        }
      }
    };

    loadAgents();
    return () => {
      mounted = false;
    };
  }, []);

  const handleRegister = async () => {
    if (!selectedAgentId || !url.trim()) {
      toast.error('Selecione um agente e informe a URL do endpoint.');
      return;
    }

    setSubmitting(true);
    try {
      const result = await api.registerAgentCallback(selectedAgentId, url.trim());
      setRegistration({ webhook_id: result.webhook_id, secret: result.secret });
      setUrl('');
      toast.success('Webhook registrado com sucesso.');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Falha ao registrar webhook.';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Webhooks</h1>
        <button className="btn btn-primary w-full sm:w-auto" onClick={handleRegister} disabled={submitting || loadingAgents}>
          {submitting ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />} Add Endpoint
        </button>
      </div>

      <div className="card space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700" htmlFor="webhook-agent">
            Agent
          </label>
          <select
            id="webhook-agent"
            value={selectedAgentId}
            onChange={(event) => setSelectedAgentId(event.target.value)}
            className="input-field"
            disabled={loadingAgents || submitting}
          >
            <option value="">{loadingAgents ? 'Loading agents...' : 'Select an agent'}</option>
            {agents.map(agent => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700" htmlFor="webhook-url">
            Callback URL
          </label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              id="webhook-url"
              type="url"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://example.com/agent-callback"
              className="input-field"
              disabled={submitting}
            />
            <button className="btn btn-primary sm:w-auto" onClick={handleRegister} disabled={submitting || loadingAgents}>
              {submitting ? <Loader2 size={18} className="animate-spin" /> : <WebhookIcon size={18} />}
              Register
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Este portal registra callbacks reais via API. A listagem e revogação de webhooks ainda não estão expostas no frontend.
        </div>

        {registration && (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
            <div className="font-semibold">Webhook registrado</div>
            <div className="mt-2 font-mono text-xs break-all">ID: {registration.webhook_id}</div>
            <div className="mt-1 font-mono text-xs break-all">Secret: {registration.secret}</div>
          </div>
        )}
      </div>
    </div>
  );
};
