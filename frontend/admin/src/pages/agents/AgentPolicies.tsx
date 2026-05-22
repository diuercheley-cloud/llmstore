import React, { useState } from 'react';
import { ShieldCheck, Search, FileText } from 'lucide-react';
import { PolicyDecisionPanel } from '../../components/agents/PolicyDecisionPanel';

export default function AgentPolicies() {
  const policies = [
    { name: "max_steps_by_risk", status: "active" },
    { name: "allowed_tools_by_agent", status: "active" },
    { name: "no_shell_tool_by_default", status: "active" },
    { name: "approval_required_for_destructive_tools", status: "active" },
    { name: "sovereign_isolation", status: "evaluating" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black tracking-tight">Agent <span className="text-primary">Policies</span></h1>
          <p className="text-muted-foreground mt-2 text-lg">Governança centralizada e Policy-as-Code para agentes.</p>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
            <h3 className="font-black uppercase tracking-widest text-muted-foreground mb-4">Políticas Globais</h3>
            <PolicyDecisionPanel policies={policies} />
          </div>
          
          <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
             <h3 className="font-black uppercase tracking-widest text-muted-foreground mb-4">Simulação de Política</h3>
             <p className="text-sm text-muted-foreground mb-4">Teste o efeito das políticas em uma ação específica (Dry Run).</p>
             <div className="space-y-4">
               <div>
                 <label className="block text-xs font-black uppercase text-muted-foreground tracking-widest mb-2">Ação (JSON)</label>
                 <textarea className="w-full h-32 bg-background border border-border rounded-xl p-3 font-mono text-xs focus:ring-2 focus:ring-primary outline-none resize-none" defaultValue='{&#10;  "task_type": "tool_call",&#10;  "tool_name": "delete_database"&#10;}'></textarea>
               </div>
               <button className="bg-primary text-primary-foreground font-bold px-6 py-2.5 rounded-xl hover:opacity-90">Simular Ação</button>
             </div>
          </div>
        </div>
        
        <div>
          <div className="bg-card border border-border rounded-3xl p-6 shadow-sm sticky top-24">
            <h3 className="font-black uppercase tracking-widest text-muted-foreground mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              Policy-as-Code
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              As políticas são definidas em arquivos YAML no repositório e aplicadas dinamicamente pelo <span className="font-bold text-foreground">AgentRiskEngine</span>.
            </p>
            <div className="p-4 bg-secondary/30 rounded-xl border border-border">
              <pre className="text-[10px] font-mono text-muted-foreground overflow-x-auto">
{`- name: block_destructive
  description: "Block drops"
  rules:
    - if: "tool_name matches (delete)"
      then: { action: "require_approval" }`}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
