import React from 'react';
import { CheckCircle2, XCircle, BarChart } from 'lucide-react';

interface EvalResultProps {
  score: number;
  passRate: number;
  version: string;
  createdAt: string;
}

export function EvalResultCard({ score, passRate, version, createdAt }: EvalResultProps) {
  const isPassing = passRate >= 0.8; // Example threshold

  return (
    <div className={`p-6 rounded-2xl border ${isPassing ? 'border-green-500/30 bg-green-500/5' : 'border-destructive/30 bg-destructive/5'}`}>
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-sm font-black uppercase tracking-widest text-muted-foreground mb-1">Baseline de Avaliação</h3>
          <p className="text-2xl font-black text-foreground">Versão {version}</p>
        </div>
        <div className={`p-3 rounded-xl ${isPassing ? 'bg-green-500/20 text-green-600' : 'bg-destructive/20 text-destructive'}`}>
          {isPassing ? <CheckCircle2 className="w-6 h-6" /> : <XCircle className="w-6 h-6" />}
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <span className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider">Pass Rate</span>
          <p className="text-xl font-mono font-bold mt-1">{(passRate * 100).toFixed(1)}%</p>
        </div>
        <div>
          <span className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider">Score Global</span>
          <p className="text-xl font-mono font-bold mt-1">{(score * 100).toFixed(1)}/100</p>
        </div>
      </div>
      
      <div className="mt-6 pt-4 border-t border-border/50 flex justify-between items-center text-xs text-muted-foreground">
        <span>Avaliado em: {new Date(createdAt).toLocaleDateString()}</span>
        <button className="font-bold text-primary hover:underline flex items-center gap-1">
          <BarChart size={14} /> Ver Relatório Completo
        </button>
      </div>
    </div>
  );
}
