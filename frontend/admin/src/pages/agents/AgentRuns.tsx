import React from 'react';
import { Activity, Search, ChevronRight } from 'lucide-react';
import { AgentStatusBadge } from '../../components/agents/AgentStatusBadge';
import { Link } from 'react-router-dom';

export default function AgentRuns() {
  // Mock data
  const runs = [
    { id: "run_abc123", agent: "Support Triage", status: "executing", steps: 4, started_at: "2026-05-21T10:30:00Z" },
    { id: "run_def456", agent: "Billing Auditor", status: "completed", steps: 12, started_at: "2026-05-21T09:15:00Z" },
    { id: "run_ghi789", agent: "DB Admin Ops", status: "failed", steps: 2, started_at: "2026-05-21T08:00:00Z" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
      <header>
        <h1 className="text-4xl font-black tracking-tight">Agent <span className="text-primary">Runs</span></h1>
        <p className="text-muted-foreground mt-2 text-lg">Histórico e monitoramento de execuções de agentes.</p>
      </header>

      <div className="bg-card border border-border rounded-3xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-border bg-secondary/30 flex gap-4">
           <div className="relative flex-1 max-w-md">
             <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
             <input type="text" placeholder="Buscar por ID ou Agente..." className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-lg text-sm focus:ring-2 focus:ring-primary outline-none" />
           </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-secondary/30 text-muted-foreground text-[10px] font-black uppercase tracking-widest border-b border-border">
                <th className="px-6 py-4">Run ID</th>
                <th className="px-6 py-4">Agente</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Passos</th>
                <th className="px-6 py-4">Iniciado Em</th>
                <th className="px-6 py-4 text-right"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {runs.map(run => (
                <tr key={run.id} className="hover:bg-secondary/50 transition-colors group">
                  <td className="px-6 py-4 font-mono text-xs text-muted-foreground">{run.id}</td>
                  <td className="px-6 py-4 font-bold text-sm">{run.agent}</td>
                  <td className="px-6 py-4"><AgentStatusBadge status={run.status} /></td>
                  <td className="px-6 py-4 text-sm">{run.steps}</td>
                  <td className="px-6 py-4 text-xs text-muted-foreground">{new Date(run.started_at).toLocaleString()}</td>
                  <td className="px-6 py-4 text-right">
                    <Link to={`/agents/runs/${run.id}`} className="inline-flex p-2 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg transition-colors">
                      <ChevronRight size={18} />
                    </Link>
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
