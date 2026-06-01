import React, { useEffect, useState } from 'react';
import { Bot, Plus, Search, Loader2 } from 'lucide-react';
import { AgentStatusBadge } from '../../components/agents/AgentStatusBadge';
import { AgentRiskBadge } from '../../components/agents/AgentRiskBadge';
import api from '../../lib/api';

export default function AgentRegistry() {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listAgentRegistry()
      .then(setAgents)
      .catch(err => console.error("Failed to load agents", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black tracking-tight">Agent <span className="text-primary">Registry</span></h1>
          <p className="text-muted-foreground mt-2 text-lg">Catálogo e definições de agentes no sistema.</p>
        </div>
        <button className="bg-primary text-primary-foreground px-4 py-2.5 rounded-xl font-bold flex items-center gap-2 hover:opacity-90 transition-opacity">
          <Plus size={18} /> Novo Agente
        </button>
      </header>

      <div className="bg-card border border-border rounded-3xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-border bg-secondary/30 flex gap-4">
           <div className="relative flex-1 max-w-md">
             <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
             <input type="text" placeholder="Buscar agentes..." className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-lg text-sm focus:ring-2 focus:ring-primary outline-none" />
           </div>
        </div>
        
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-20 flex flex-col items-center justify-center gap-4 text-muted-foreground">
              <Loader2 className="w-8 h-8 animate-spin" />
              <p className="text-sm font-medium">Carregando catálogo de agentes...</p>
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-secondary/30 text-muted-foreground text-[10px] font-black uppercase tracking-widest border-b border-border">
                  <th className="px-6 py-4">Nome & Versão</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Risco</th>
                  <th className="px-6 py-4">Dono</th>
                  <th className="px-6 py-4 text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {agents.map(agent => (
                  <tr key={agent.id} className="hover:bg-secondary/50 transition-colors cursor-pointer">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                          <Bot size={16} />
                        </div>
                        <div>
                          <h4 className="font-bold text-foreground text-sm">{agent.name}</h4>
                          <span className="text-[10px] font-mono text-muted-foreground block mt-0.5">v{agent.semantic_version || agent.version}</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4"><AgentStatusBadge status={agent.status} /></td>
                    <td className="px-6 py-4"><AgentRiskBadge level={agent.risk_level || agent.risk} /></td>
                    <td className="px-6 py-4 text-xs font-mono">{agent.owner}</td>
                    <td className="px-6 py-4 text-right">
                      <button className="text-primary text-xs font-bold hover:underline">Ver Detalhes</button>
                    </td>
                  </tr>
                ))}
                {agents.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-20 text-center text-muted-foreground text-sm">
                      Nenhum agente registrado.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
