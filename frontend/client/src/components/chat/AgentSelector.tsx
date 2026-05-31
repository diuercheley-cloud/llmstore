import { useState, useEffect } from 'react';
import { Bot, ChevronDown, Check } from 'lucide-react';
import { api } from '../../lib/api';
import type { Agent } from '../../lib/types';

interface AgentSelectorProps {
  selectedAgentId: string | null;
  onSelect: (agent: Agent) => void;
}

export function AgentSelector({ selectedAgentId, onSelect }: AgentSelectorProps) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadAgents() {
      setLoading(true);
      try {
        const list = await api.listAgents();
        setAgents(list.filter(a => a.status === 'active'));
        // Auto-select first if none selected
        if (!selectedAgentId && list.length > 0) {
          const active = list.find(a => a.status === 'active') || list[0];
          onSelect(active);
        }
      } catch (err) {
        console.error('Failed to load agents', err);
      } finally {
        setLoading(false);
      }
    }
    loadAgents();
  }, [onSelect, selectedAgentId]);

  const selectedAgent = agents.find(a => a.id === selectedAgentId);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between gap-3 px-3 py-2 bg-white border border-border-base rounded-xl hover:border-primary/50 transition-all text-left group"
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <Bot size={18} className="text-primary" />
          </div>
          <div className="min-w-0">
            <div className="text-xs font-bold text-text-base uppercase tracking-tight">Active Agent</div>
            <div className="text-sm font-medium text-slate-600 truncate">
              {loading ? 'Loading...' : selectedAgent ? selectedAgent.name : 'Select Agent'}
            </div>
          </div>
        </div>
        <ChevronDown size={16} className={`text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-border-base rounded-xl shadow-xl z-50 overflow-hidden py-1">
          {agents.length === 0 && !loading && (
            <div className="px-4 py-3 text-sm text-slate-500 italic">No active agents found</div>
          )}
          {agents.map(agent => (
            <button
              key={agent.id}
              onClick={() => {
                onSelect(agent);
                setIsOpen(false);
              }}
              className="w-full flex items-center justify-between gap-3 px-4 py-2 hover:bg-slate-50 transition-colors text-left"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-6 h-6 rounded bg-slate-100 flex items-center justify-center shrink-0">
                  <Bot size={14} className="text-slate-500" />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-medium text-text-base truncate">{agent.name}</div>
                  <div className="text-[10px] text-slate-400 font-mono">v{agent.version}</div>
                </div>
              </div>
              {agent.id === selectedAgentId && <Check size={14} className="text-primary shrink-0" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
