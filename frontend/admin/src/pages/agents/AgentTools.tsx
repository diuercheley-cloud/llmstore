import React from 'react';
import { Wrench, ShieldAlert } from 'lucide-react';
import { ToolInvocationCard } from '../../components/agents/ToolInvocationCard';

export default function AgentTools() {
  const tools = [
    { name: "search_knowledge_base", success: true, latencyMs: 340, outputSummary: "Encontrados 3 artigos relevantes." },
    { name: "assign_ticket", success: true, latencyMs: 800, outputSummary: "Ticket #1234 atribuído a support_tier1" },
    { name: "delete_database", success: false, error: "Policy denial: Destructive tool requires human approval." },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
      <header>
        <h1 className="text-4xl font-black tracking-tight">Agent <span className="text-primary">Tools</span></h1>
        <p className="text-muted-foreground mt-2 text-lg">Monitoramento de invocação de ferramentas por agentes.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          <h3 className="font-black uppercase tracking-widest text-muted-foreground mb-4">Invocações Recentes</h3>
          {tools.map((tool, idx) => (
            <ToolInvocationCard key={idx} toolName={tool.name} success={tool.success} latencyMs={tool.latencyMs} outputSummary={tool.outputSummary} error={tool.error} />
          ))}
        </div>
        
        <div>
          <div className="bg-card border border-border rounded-3xl p-6 shadow-sm sticky top-24">
            <h3 className="font-black uppercase tracking-widest text-muted-foreground mb-4 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-primary" />
              Ferramentas Bloqueadas
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              Ferramentas com alto índice de bloqueio por políticas de segurança nas últimas 24h.
            </p>
            <ul className="space-y-3">
              <li className="flex justify-between items-center text-sm p-3 bg-secondary/30 rounded-xl">
                <span className="font-mono font-bold">delete_database</span>
                <span className="text-destructive font-bold">12 blocks</span>
              </li>
              <li className="flex justify-between items-center text-sm p-3 bg-secondary/30 rounded-xl">
                <span className="font-mono font-bold">execute_shell</span>
                <span className="text-destructive font-bold">5 blocks</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
