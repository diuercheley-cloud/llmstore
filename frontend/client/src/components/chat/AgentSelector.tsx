import { useState, useEffect } from 'react';
import { ChevronDown, Bot, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';
import type { Agent } from '../../lib/types';

interface AgentSelectorProps {
  selectedAgentId: string | null;
  onSelect: (agent: Agent) => void;
}

export function AgentSelector({ selectedAgentId, onSelect }: AgentSelectorProps) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.listAgents();
        if (!cancelled) {
          setAgents(data.filter(a => a.status === 'active'));
          setLoading(false);
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err.message || 'Failed to load agents');
          setLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const selected = agents.find(a => a.id === selectedAgentId);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-500 px-3 py-2">
        <Loader2 size={16} className="animate-spin" />
        Loading agents...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-500 px-3 py-2 bg-red-50 rounded-lg">
        {error}
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div className="text-sm text-slate-400 px-3 py-2">
        No active agents found
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-2 bg-white border border-border-base rounded-lg hover:bg-slate-50 transition-colors w-full text-left"
      >
        <Bot size={18} className="text-primary shrink-0" />
        <span className="flex-1 truncate font-medium text-sm">
          {selected ? selected.name : 'Select an agent...'}
        </span>
        <ChevronDown
          size={16}
          className={`text-slate-400 transition-transform shrink-0 ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 right-0 top-full mt-1 z-20 bg-white border border-border-base rounded-lg shadow-lg max-h-60 overflow-y-auto">
            {agents.map(agent => (
              <button
                key={agent.id}
                onClick={() => { onSelect(agent); setOpen(false); }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-slate-50 transition-colors ${
                  agent.id === selectedAgentId ? 'bg-primary/5 text-primary' : 'text-text-base'
                }`}
              >
                <Bot size={16} className="shrink-0" />
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">{agent.name}</div>
                  <div className="text-xs text-slate-400">v{agent.version}</div>
                </div>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
