import React from 'react';
import { Info, ChevronRight, FileCode } from 'lucide-react';
import type { StudioFlowNode } from './studioData';

interface EvalConfigPanelProps {
  selectedNode: StudioFlowNode | null;
}

const statusLabel: Record<StudioFlowNode['status'], string> = {
  idle: 'Aguardando',
  running: 'Em execução',
  success: 'Concluido',
  failed: 'Falhou',
};

export default function EvalConfigPanel({ selectedNode }: EvalConfigPanelProps) {
  if (!selectedNode) return null;

  return (
    <div className="p-6">
      <div className="flex items-center gap-2 mb-6">
        <Info size={16} className="text-blue-400" />
        <h2 className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">
          Detalhes Técnicos
        </h2>
      </div>

      <div className="space-y-4">
        <div className="flex justify-between items-center text-xs">
          <span className="text-slate-500 font-medium">Status Atual</span>
          <span className={`font-bold ${
            selectedNode.status === 'success' ? 'text-emerald-400' :
            selectedNode.status === 'running' ? 'text-amber-400' : 'text-slate-400'
          }`}>
            {statusLabel[selectedNode.status]}
          </span>
        </div>

        <div className="bg-white/5 border border-white/5 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-300">
            <FileCode size={14} className="text-slate-500" />
            Configuração Bruta
          </div>
          <div className="font-mono text-[10px] text-slate-500 break-all bg-black/20 p-2 rounded-lg border border-white/5">
            {selectedNode.config}
          </div>
        </div>

        <div className="space-y-2">
          <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Próxima Ação</span>
          <div className="flex gap-2 text-[11px] text-blue-300 leading-relaxed">
            <ChevronRight size={14} className="flex-shrink-0 mt-0.5" />
            {selectedNode.nextStep}
          </div>
        </div>
      </div>
    </div>
  );
}

