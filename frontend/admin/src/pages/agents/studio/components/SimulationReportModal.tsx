import React from 'react';
import { X, Mail, FileText, Terminal, Globe, Database, AlertCircle, CheckCircle2 } from 'lucide-react';

interface InterceptedAction {
  step: number;
  toolName: string;
  category: 'email' | 'filesystem' | 'shell' | 'APIs' | 'database writes';
  parameters: any;
  output: any;
}

interface SimulationReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: {
    totalIntercepted: number;
    categories: {
      email: number;
      filesystem: number;
      shell: number;
      APIs: number;
      'database writes': number;
    };
    actions: InterceptedAction[];
  };
}

export default function SimulationReportModal({ isOpen, onClose, report }: SimulationReportModalProps) {
  if (!isOpen) return null;

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'email': return <Mail className="w-5 h-5 text-sky-400" />;
      case 'filesystem': return <FileText className="w-5 h-5 text-amber-400" />;
      case 'shell': return <Terminal className="w-5 h-5 text-emerald-400" />;
      case 'APIs': return <Globe className="w-5 h-5 text-purple-400" />;
      case 'database writes': return <Database className="w-5 h-5 text-indigo-400" />;
      default: return <AlertCircle className="w-5 h-5 text-slate-400" />;
    }
  };

  const getCategoryBg = (category: string) => {
    switch (category) {
      case 'email': return 'bg-sky-500/10 border-sky-500/20';
      case 'filesystem': return 'bg-amber-500/10 border-amber-500/20';
      case 'shell': return 'bg-emerald-500/10 border-emerald-500/20';
      case 'APIs': return 'bg-purple-500/10 border-purple-500/20';
      case 'database writes': return 'bg-indigo-500/10 border-indigo-500/20';
      default: return 'bg-slate-500/10 border-slate-500/20';
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
      <div className="relative w-full max-w-4xl max-h-[85vh] flex flex-col bg-slate-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
              <Terminal className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">Simulation Mode Report</h2>
              <p className="text-xs text-slate-400">Workflow dry-run results with zero side effects</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Status and Summary Header */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-xl gap-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 animate-pulse" />
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-emerald-400 uppercase tracking-wide">Success (Simulated)</span>
                  <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-bold">DRY_RUN</span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  All side effects were intercepted successfully. No actual data was modified.
                </p>
              </div>
            </div>
            <div className="text-right sm:border-l sm:border-white/10 sm:pl-6">
              <span className="text-2xl font-black text-slate-100">{report.totalIntercepted}</span>
              <p className="text-[10px] uppercase font-bold tracking-widest text-slate-500 mt-0.5">Actions Intercepted</p>
            </div>
          </div>

          {/* Cards Grid */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Intercepted Categories</h3>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {(Object.keys(report.categories) as Array<keyof typeof report.categories>).map((cat) => (
                <div 
                  key={cat}
                  className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all ${getCategoryBg(cat)}`}
                >
                  <div className="mb-2">{getCategoryIcon(cat)}</div>
                  <span className="text-sm font-bold text-slate-200 capitalize text-center leading-tight">
                    {cat === 'APIs' ? 'APIs' : cat}
                  </span>
                  <span className="text-lg font-black text-slate-100 mt-1">
                    {report.categories[cat]}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions Timeline */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Interception Trace</h3>
            <div className="space-y-4">
              {report.actions.map((act) => (
                <div 
                  key={act.step}
                  className="flex gap-4 p-4 bg-slate-950/40 border border-white/5 rounded-xl hover:border-white/10 transition-colors"
                >
                  <div className="flex flex-col items-center">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-800 text-[10px] font-bold text-slate-400 border border-white/5">
                      {act.step}
                    </span>
                    <div className="w-0.5 flex-1 bg-white/5 my-2" />
                  </div>
                  
                  <div className="flex-1 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-slate-200">{act.toolName}</span>
                        <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase border ${getCategoryBg(act.category)}`}>
                          {act.category}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-500">Timestamp: Simulated Step {act.step}</span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px] font-mono">
                      {/* Parameters */}
                      <div className="bg-slate-950/60 p-3 rounded-lg border border-white/5">
                        <span className="text-slate-500 font-bold block mb-1.5 uppercase tracking-wider text-[9px]">Intercepted Parameters</span>
                        <pre className="text-slate-300 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(act.parameters, null, 2)}</pre>
                      </div>

                      {/* Simulated Output */}
                      <div className="bg-slate-950/60 p-3 rounded-lg border border-white/5">
                        <span className="text-slate-500 font-bold block mb-1.5 uppercase tracking-wider text-[9px]">Simulated Output</span>
                        <pre className="text-emerald-400/90 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(act.output, null, 2)}</pre>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-4 border-t border-white/5 bg-slate-900/50 gap-3">
          <button 
            onClick={onClose}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-indigo-600/10 transition-all active:scale-95"
          >
            Close Report
          </button>
        </div>

      </div>
    </div>
  );
}
