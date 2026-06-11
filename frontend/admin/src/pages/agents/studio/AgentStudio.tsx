import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Play, Shield, Zap, Save, ChevronRight, Activity, GitBranch, Workflow } from 'lucide-react';
import { toast } from 'sonner';
import FlowBuilder from './FlowBuilder';
import ToolPalette from './ToolPalette';
import MemoryConfigPanel from './MemoryConfigPanel';
import EvalConfigPanel from './EvalConfigPanel';
import DebuggerPanel from './DebuggerPanel';
import AgentGraphView from './AgentGraphView';
import { studioFlowNodes } from './studioData';
import SimulationReportModal from './components/SimulationReportModal';

type StudioTab = 'flow' | 'graph';

export default function AgentStudio() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<StudioTab>('flow');
  const [nodes, setNodes] = useState(studioFlowNodes);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [simulationReport, setSimulationReport] = useState<any>(null);
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

  const handleSimulationRun = async () => {
    setIsSimulating(true);
    toast.info('Starting workflow in simulation mode...');
    try {
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const mockReport = {
        totalIntercepted: 5,
        categories: {
          email: 1,
          filesystem: 1,
          shell: 1,
          APIs: 1,
          'database writes': 1
        },
        actions: [
          {
            step: 1,
            toolName: 'read_config_file',
            category: 'filesystem' as const,
            parameters: { path: './config/production.json', format: 'json' },
            output: { status: 'success', data: { api_version: 'v2', db_pool: 10 }, simulated: true }
          },
          {
            step: 2,
            toolName: 'query_user_account',
            category: 'database writes' as const,
            parameters: { query: 'INSERT INTO audit_log (event, user_id) VALUES ("login", 992)', user_id: 992 },
            output: { status: 'success', rows_affected: 1, last_insert_id: 10421, simulated: true }
          },
          {
            step: 3,
            toolName: 'fetch_billing_status',
            category: 'APIs' as const,
            parameters: { url: 'https://billing.platform.internal/v1/status', method: 'GET' },
            output: { status: 'success', status_code: 200, data: { active: true, balance_brl: 450.25 }, simulated: true }
          },
          {
            step: 4,
            toolName: 'send_admin_alert',
            category: 'email' as const,
            parameters: { to: 'ops@company.com', subject: '[ALERT] Budget threshold reached', body: 'Agent has consumed 80% of daily quota' },
            output: { status: 'success', message: 'Email sent successfully (simulated)', simulated: true }
          },
          {
            step: 5,
            toolName: 'run_system_cleanup',
            category: 'shell' as const,
            parameters: { command: 'rm -rf /tmp/cache/*' },
            output: { status: 'success', exit_code: 0, stdout: 'Simulated command execution output', stderr: '', simulated: true }
          }
        ]
      };
      
      setSimulationReport(mockReport);
      toast.success('Simulation run completed successfully!');
      setIsReportOpen(true);
    } catch (e) {
      toast.error('Simulation run failed.');
    } finally {
      setIsSimulating(false);
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
          {/* Tab Switcher */}
          <div className="flex items-center bg-white/5 rounded-xl p-0.5 border border-white/10">
            <button
              onClick={() => setActiveTab('flow')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'flow' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Workflow size={14} /> Flow Builder
            </button>
            <button
              onClick={() => setActiveTab('graph')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'graph' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'
              }`}
            >
              <GitBranch size={14} /> Agent Graph
            </button>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20 text-xs font-bold mr-4">
            <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
            LIVE MODE
          </div>
          
          {activeTab === 'flow' && (
            <>
              <button 
                onClick={handleValidate}
                disabled={isValidating}
                className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-sm font-semibold transition-all disabled:opacity-50"
              >
                {isValidating ? <Activity size={16} className="animate-spin" /> : <Shield size={16} className="text-slate-400" />}
                {isValidating ? 'Validating...' : 'Validate DAG'}
              </button>

              <button 
                onClick={handleSimulationRun}
                disabled={isSimulating}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-500/20 rounded-xl text-sm font-bold shadow-lg shadow-indigo-500/10 transition-all active:scale-95 disabled:opacity-50"
              >
                {isSimulating ? <Activity size={16} className="animate-spin" /> : <Play size={16} className="text-indigo-200" />}
                {isSimulating ? 'Simulating...' : 'Run in Simulation'}
              </button>
              
              <button 
                onClick={handleDeploy}
                disabled={isDeploying}
                className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-blue-500/20 transition-all active:scale-95 disabled:opacity-50"
              >
                {isDeploying ? <Activity size={16} className="animate-spin" /> : <Play size={16} fill="currentColor" />}
                {isDeploying ? 'Deploying...' : 'Deploy Flow'}
              </button>
            </>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {activeTab === 'flow' ? (
          <>
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
          </>
        ) : (
          /* Agent Graph Tab */
          <main className="flex-1 overflow-y-auto p-6 bg-[#020617]">
            <AgentGraphView />
          </main>
        )}
      </div>

      {simulationReport && (
        <SimulationReportModal 
          isOpen={isReportOpen}
          onClose={() => setIsReportOpen(false)}
          report={simulationReport}
        />
      )}
    </div>
  );
}

