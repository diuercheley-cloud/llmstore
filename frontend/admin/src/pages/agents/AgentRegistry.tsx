import React from 'react';
import { Bot, Plus, Search } from 'lucide-react';
import { AgentStatusBadge } from '../../components/agents/AgentStatusBadge';
import { AgentRiskBadge } from '../../components/agents/AgentRiskBadge';

export default function AgentRegistry() {
  // Mock data
  const agents = [
    { id: "1", name: "Support Triage", version: "1.0.0", status: "active", risk: "low", owner: "admin@example.com" },
    { id: "2", name: "DB Admin Ops", version: "0.9.0", status: "review", risk: "critical", owner: "ops@example.com" },
    { id: "3", name: "Billing Auditor", version: "1.2.1", status: "paused", risk: "medium", owner: "finance@example.com" },
  ];

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
                        <span className="text-[10px] font-mono text-muted-foreground block mt-0.5">v{agent.version}</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4"><AgentStatusBadge status={agent.status} /></td>
                  <td className="px-6 py-4"><AgentRiskBadge level={agent.risk} /></td>
                  <td className="px-6 py-4 text-xs font-mono">{agent.owner}</td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-primary text-xs font-bold hover:underline">Ver Detalhes</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
