import React, { useState } from 'react';
import { ArrowRight, Box, CheckCircle2, Circle, Clock } from 'lucide-react';
import type { StudioFlowNode } from './studioData';

interface FlowBuilderProps {
  nodes: StudioFlowNode[];
  onSelectNode: (id: string | null) => void;
}

export default function FlowBuilder({ nodes, onSelectNode }: FlowBuilderProps) {
  const [activeNode, setActiveNode] = useState<string | null>(null);

  const handleCardClick = (id: string) => {
    setActiveNode(id);
    onSelectNode(id);
  };

  return (
    <div className="flex-1 h-full p-12 bg-[#020617] relative overflow-auto flex flex-col items-center justify-center">
      {/* Grid background */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none" 
           style={{ backgroundImage: 'radial-gradient(#fff 1px, transparent 0)', backgroundSize: '32px 32px' }} />
      
      <div className="absolute top-6 left-6 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-700">
        <Box size={12} />
        Canvas Principal
      </div>

      <div className="flex items-center gap-12 z-10">
        {nodes.map((node, index) => {
          const isActive = activeNode === node.id;
          
          return (
            <React.Fragment key={node.id}>
              <div 
                onClick={() => handleCardClick(node.id)}
                className={`
                  relative w-64 p-5 rounded-2xl border transition-all cursor-pointer group
                  ${isActive 
                    ? 'bg-blue-500/10 border-blue-500 shadow-[0_0_30px_rgba(59,130,246,0.15)]' 
                    : 'bg-slate-900/50 border-white/5 hover:border-white/10 hover:bg-slate-900/80 shadow-xl'}
                `}
              >
                {/* Node Type Badge */}
                <div className="flex justify-between items-start mb-4">
                  <span className={`
                    text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded
                    ${node.type === 'tool_call' ? 'text-purple-400 bg-purple-400/10' : 
                      node.type === 'approval' ? 'text-amber-400 bg-amber-400/10' :
                      node.type === 'final' ? 'text-emerald-400 bg-emerald-400/10' :
                      'text-blue-400 bg-blue-400/10'}
                  `}>
                    {node.type.replace('_', ' ')}
                  </span>
                  
                  <div className="flex items-center gap-1.5">
                    {node.status === 'success' ? <CheckCircle2 size={14} className="text-emerald-500" /> :
                     node.status === 'running' ? <Clock size={14} className="text-amber-500 animate-pulse" /> :
                     <Circle size={14} className="text-slate-700" />}
                  </div>
                </div>

                <h3 className="text-sm font-bold text-white mb-1 group-hover:text-blue-400 transition-colors">
                  {node.label}
                </h3>
                <p className="text-[11px] text-slate-500 line-clamp-1 mb-4">
                  {node.config}
                </p>

                <div className="pt-3 border-t border-white/5 flex items-center justify-between">
                   <div className="text-[10px] font-medium text-slate-600 italic">
                     {node.status === 'success' ? 'Finalizado' : node.status === 'running' ? 'Processando...' : 'Aguardando'}
                   </div>
                   <div className={`w-2 h-2 rounded-full ${
                     node.status === 'success' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' :
                     node.status === 'running' ? 'bg-amber-500 animate-pulse shadow-[0_0_8px_rgba(245,158,11,0.5)]' :
                     'bg-slate-800'
                   }`} />
                </div>

                {/* Connection points */}
                <div className="absolute -left-1.5 top-1/2 -translate-y-1/2 w-3 h-3 bg-slate-900 border border-white/10 rounded-full z-20" />
                <div className="absolute -right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 bg-slate-900 border border-white/10 rounded-full z-20" />
              </div>

              {index < nodes.length - 1 && (
                <div className="relative flex items-center justify-center w-12">
                  <div className="absolute h-0.5 w-full bg-gradient-to-r from-white/5 via-white/10 to-white/5" />
                  <ArrowRight size={20} className="text-slate-700 z-10" />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

