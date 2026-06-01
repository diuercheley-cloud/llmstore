import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Play, Shield, Zap, Save, ChevronRight, Activity } from 'lucide-react';
import { toast } from 'sonner';
import FlowBuilder from './FlowBuilder';
import ToolPalette from './ToolPalette';
import MemoryConfigPanel from './MemoryConfigPanel';
import EvalConfigPanel from './EvalConfigPanel';
import DebuggerPanel from './DebuggerPanel';
import { studioFlowNodes } from './studioData';

export default function AgentStudio() {
  const navigate = useNavigate();
  const [nodes, setNodes] = useState(studioFlowNodes);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const activeNode = nodes.find((node) => node.id === selectedNode) ?? null;

  const handleAddNode = (item: any) => {
    const newNode = {
      id: Math.random().toString(36).substr(2, 9),
      type: item.type,
      label: item.label,
      status: 'idle' as const,
      config: item.description,
      summary: 'Configuração padrão para ' + item.label,
      nextStep: 'Defina o próximo passo após a execução.'
    };
    setNodes(prev => [...prev, newNode]);
    toast.success(`Nó "${item.label}" adicionado ao fluxo.`);
  };

  const handleValidate = async () => {
    setIsValidating(true);
    try {
      // Mocking validation for now as we don't have a real flow ID in the mock data
      await new Promise(resolve => setTimeout(resolve, 1500));
      toast.success('DAG validada com sucesso! Nenhum ciclo ou erro encontrado.');
    } catch (e) {
      toast.error('Falha na validação da DAG.');
    } finally {
      setIsValidating(false);
    }
  };

  const handleDeploy = async () => {
    setIsDeploying(true);
    try {
      // Mocking deployment
      await new Promise(resolve => setTimeout(resolve, 2000));
      toast.success('Fluxo publicado e versão v1.0.4 ativa no runtime.');
    } catch (e) {
      toast.error('Erro ao publicar fluxo.');
    } finally {
      setIsDeploying(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#020617] text-slate-100 font-sans overflow-hidden">
      {/* Top Header */}
      <header className="flex items-center justify-between px-6 h-16 bg-slate-900/50 backdrop-blur-xl border-b border-white/5 z-50">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/')}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors text-slate-400 hover:text-white"
            title="Voltar ao Hub"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="w-px h-6 bg-white/10 mx-1" />
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Zap className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                Agent Studio
              </h1>
              <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest font-black text-slate-500">
                <span className="text-blue-500">GA Release</span>
                <span className="opacity-50">•</span>
                <span>Enterprise Engine v2.1</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20 text-xs font-bold mr-4">
            <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
            LIVE MODE
          </div>
          
          <button 
            onClick={handleValidate}
            disabled={isValidating}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-sm font-semibold transition-all disabled:opacity-50"
          >
            {isValidating ? <Activity size={16} className="animate-spin" /> : <Shield size={16} className="text-slate-400" />}
            {isValidating ? 'Validating...' : 'Validate DAG'}
          </button>
          
          <button 
            onClick={handleDeploy}
            disabled={isDeploying}
            className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-blue-500/20 transition-all active:scale-95 disabled:opacity-50"
          >
            {isDeploying ? <Activity size={16} className="animate-spin" /> : <Play size={16} fill="currentColor" />}
            {isDeploying ? 'Deploying...' : 'Deploy Flow'}
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar: Node Library */}
        <aside className="w-72 bg-slate-950/40 border-r border-white/5 flex flex-col overflow-y-auto">
          <ToolPalette onAddNode={handleAddNode} />
        </aside>

        {/* Center: Canvas & Console */}
        <main className="flex-1 flex flex-col relative bg-[#020617]">
          <div className="flex-1 relative overflow-hidden">
             <FlowBuilder nodes={nodes} onSelectNode={setSelectedNode} />
          </div>

          {/* Debug Console */}
          <div className="h-72 border-t border-white/5">
            <DebuggerPanel />
          </div>
        </main>

        {/* Right Panel: Configuration */}
        <aside className="w-80 bg-slate-950/40 border-l border-white/5 flex flex-col overflow-y-auto">
          <div className="flex flex-col flex-1">
            <MemoryConfigPanel nodes={nodes} selectedNode={activeNode} />
            <EvalConfigPanel selectedNode={activeNode} />
            
            {!activeNode && (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500">
                <Activity size={32} className="mb-4 opacity-20" />
                <p className="text-sm">Selecione um nó no canvas para configurar parâmetros, políticas e evals.</p>
              </div>
            )}
          </div>
          
          <div className="p-4 border-t border-white/5 bg-slate-900/30">
            <button className="w-full flex items-center justify-center gap-2 py-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-sm font-medium transition-colors">
              <Save size={16} />
              Save Draft
            </button>
          </div>
        </aside>
      </div>
    </div>
  );
}

