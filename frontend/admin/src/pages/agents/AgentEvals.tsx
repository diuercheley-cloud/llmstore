import React from 'react';
import { ShieldAlert, BarChart } from 'lucide-react';
import { EvalResultCard } from '../../components/agents/EvalResultCard';

export default function AgentEvals() {
  const evals = [
    { score: 0.95, passRate: 1.0, version: "1.0.0", createdAt: "2026-05-21T08:00:00Z" },
    { score: 0.75, passRate: 0.7, version: "0.9.0", createdAt: "2026-05-20T08:00:00Z" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
      <header>
        <h1 className="text-4xl font-black tracking-tight">Agent <span className="text-primary">Evals</span></h1>
        <p className="text-muted-foreground mt-2 text-lg">Resultados de avaliações de segurança e performance (Baselines).</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {evals.map((e, idx) => (
          <EvalResultCard key={idx} {...e} />
        ))}
      </div>
      
      {evals.length === 0 && (
         <div className="text-center p-12 border border-dashed border-border rounded-3xl">
           <BarChart className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-50" />
           <h3 className="text-lg font-bold text-foreground mb-2">Nenhum Eval Encontrado</h3>
           <p className="text-muted-foreground">O Agent Evaluation Framework pode estar desabilitado ou não há dados.</p>
         </div>
      )}
    </div>
  );
}
