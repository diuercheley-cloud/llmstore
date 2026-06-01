import React from 'react';
import { BarChart3, Target, Activity, ShieldCheck, Settings2 } from 'lucide-react';
import type { StudioFlowNode } from './studioData';

interface MemoryConfigPanelProps {
  nodes: StudioFlowNode[];
  selectedNode: StudioFlowNode | null;
}

export default function MemoryConfigPanel({ nodes, selectedNode }: MemoryConfigPanelProps) {
  const runningCount = nodes.filter((node) => node.status === 'running').length;
  const approvalCount = nodes.filter((node) => node.type === 'approval').length;
  const completedCount = nodes.filter((node) => node.status === 'success').length;

  return (
    <div className="p-6 border-b border-white/5 bg-white/[0.01]">
      <div className="flex items-center gap-2 mb-6">
        <BarChart3 size={16} className="text-blue-400" />
        <h2 className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">
          Resumo do Fluxo
        </h2>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-6">
        <div className="bg-white/5 border border-white/5 p-3 rounded-xl">
          <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1">Total</div>
          <div className="text-xl font-black text-white">{nodes.length}</div>
        </div>
        <div className="bg-emerald-500/10 border border-emerald-500/10 p-3 rounded-xl">
          <div className="text-[10px] font-black uppercase tracking-widest text-emerald-500/60 mb-1">OK</div>
          <div className="text-xl font-black text-emerald-400">{completedCount}</div>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs px-1">
          <div className="flex items-center gap-2 text-slate-400 font-medium">
            <Activity size={12} className="text-amber-500" />
            Em andamento
          </div>
          <span className="font-bold text-white">{runningCount}</span>
        </div>
        <div className="flex items-center justify-between text-xs px-1">
          <div className="flex items-center gap-2 text-slate-400 font-medium">
            <ShieldCheck size={12} className="text-blue-400" />
            Aprovações
          </div>
          <span className="font-bold text-white">{approvalCount}</span>
        </div>
      </div>

      <div className="mt-8 pt-6 border-t border-white/5">
        <div className="flex items-center gap-2 mb-4">
          <Target size={16} className="text-indigo-400" />
          <h2 className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">
            Foco Operacional
          </h2>
        </div>
        
        <div className="bg-slate-900/50 rounded-xl p-4 border border-white/5">
          {selectedNode ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-blue-400">
                <Settings2 size={12} />
                {selectedNode.label}
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed italic">
                "{selectedNode.summary}"
              </p>
            </div>
          ) : (
            <p className="text-[11px] text-slate-500 leading-relaxed text-center">
              Selecione um nó no canvas para visualizar o contexto operacional.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

