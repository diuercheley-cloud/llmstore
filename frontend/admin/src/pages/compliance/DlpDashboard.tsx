import React, { useEffect, useState } from 'react';
import { 
  ShieldAlert, ShieldCheck, ArrowDownLeft, ArrowUpRight, Slash, 
  RefreshCw, Database, Eye, Terminal, Mail, Key, Globe, FileText, 
  Trash2, AlertTriangle, AlertCircle
} from 'lucide-react';
import api from '../../lib/api';
import { toast } from 'sonner';

interface DLPFinding {
  type: string;
  value: string;
  start: number;
  end: number;
  method: string;
}

interface DLPViolation {
  id: string;
  run_id: string | null;
  tenant_id: string;
  direction: 'ingress' | 'egress';
  content_type: 'prompt' | 'response' | 'tool_output';
  findings: DLPFinding[];
  action_taken: 'redacted' | 'blocked' | 'allowed';
  created_at: string;
}

interface DLPStats {
  total_violations: number;
  by_category: Record<string, number>;
  by_direction: { ingress: number; egress: number };
  by_action: Record<string, number>;
}

export default function DlpDashboard() {
  const [violations, setViolations] = useState<DLPViolation[]>([]);
  const [stats, setStats] = useState<DLPStats>({
    total_violations: 0,
    by_category: {},
    by_direction: { ingress: 0, egress: 0 },
    by_action: {},
  });
  const [loading, setLoading] = useState(false);
  const [selectedViolation, setSelectedViolation] = useState<DLPViolation | null>(null);

  const fetchDlpData = async () => {
    setLoading(true);
    try {
      const violationsData = await api.listDlpViolations();
      const statsData = await api.getDlpStats();
      setViolations(violationsData);
      setStats(statsData);
    } catch (e) {
      toast.error('Erro ao buscar dados do DLP.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDlpData();
  }, []);

  const getPiiIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'email': return <Mail className="w-4 h-4 text-sky-400" />;
      case 'cpf':
      case 'rg': return <FileText className="w-4 h-4 text-amber-400" />;
      case 'credit_card': return <Database className="w-4 h-4 text-rose-400" />;
      case 'jwt': return <Globe className="w-4 h-4 text-purple-400" />;
      case 'api_key':
      case 'aws_access_key':
      case 'aws_secret_key': return <Key className="w-4 h-4 text-indigo-400" />;
      default: return <AlertCircle className="w-4 h-4 text-slate-400" />;
    }
  };

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'redacted':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full text-[10px] font-bold uppercase">
            <ShieldCheck size={12} /> Redacted
          </span>
        );
      case 'blocked':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-full text-[10px] font-bold uppercase">
            <Slash size={12} /> Blocked
          </span>
        );
      case 'allowed':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-full text-[10px] font-bold uppercase">
            <AlertTriangle size={12} /> Allowed
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 bg-slate-500/10 border border-slate-500/20 text-slate-400 rounded-full text-[10px] font-bold uppercase">
            {action}
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#020617] text-slate-100 font-sans p-6 overflow-y-auto">
      
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-black bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            DLP Compliance Dashboard
          </h1>
          <p className="text-slate-400 text-xs mt-1">
            Data Loss Prevention: Real-time sensitive data auditing and prompt/response leak prevention.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={fetchDlpData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 border border-white/10 hover:bg-white/10 rounded-lg text-xs font-semibold transition-all disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </header>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
        
        {/* Metric 1 */}
        <div className="p-4 bg-slate-900/50 border border-white/5 rounded-2xl flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Total Incidents</span>
            <span className="text-2xl font-black text-slate-200 mt-1 block">{stats.total_violations}</span>
          </div>
          <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-xl">
            <ShieldAlert size={20} />
          </div>
        </div>

        {/* Metric 2 */}
        <div className="p-4 bg-slate-900/50 border border-white/5 rounded-2xl flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Ingress (Prompts)</span>
            <span className="text-2xl font-black text-slate-200 mt-1 block">{stats.by_direction.ingress}</span>
          </div>
          <div className="p-3 bg-sky-500/10 border border-sky-500/20 text-sky-400 rounded-xl">
            <ArrowDownLeft size={20} />
          </div>
        </div>

        {/* Metric 3 */}
        <div className="p-4 bg-slate-900/50 border border-white/5 rounded-2xl flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Egress (Outputs)</span>
            <span className="text-2xl font-black text-slate-200 mt-1 block">{stats.by_direction.egress}</span>
          </div>
          <div className="p-3 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-xl">
            <ArrowUpRight size={20} />
          </div>
        </div>

        {/* Metric 4 */}
        <div className="p-4 bg-slate-900/50 border border-white/5 rounded-2xl flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Redacted Matches</span>
            <span className="text-2xl font-black text-slate-200 mt-1 block">{stats.by_action.redacted || 0}</span>
          </div>
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl">
            <ShieldCheck size={20} />
          </div>
        </div>

        {/* Metric 5 */}
        <div className="p-4 bg-slate-900/50 border border-white/5 rounded-2xl flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Blocked Leaks</span>
            <span className="text-2xl font-black text-slate-200 mt-1 block">{stats.by_action.blocked || 0}</span>
          </div>
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl">
            <Slash size={20} />
          </div>
        </div>

      </div>

      {/* Main Grid: Statistics Chart & Incident Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        
        {/* Left Column: Category Breakdown */}
        <div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-200 mb-1">Violation Breakdown</h3>
            <p className="text-[10px] text-slate-500 uppercase font-black tracking-wider mb-6">Sensitive Data Distribution</p>
            
            <div className="space-y-4">
              {Object.keys(stats.by_category).length === 0 ? (
                <div className="text-center py-12 text-slate-600 text-xs">No scan events recorded</div>
              ) : (
                Object.keys(stats.by_category).map((cat) => {
                  const val = stats.by_category[cat];
                  const percentage = Math.round((val / (stats.total_violations || 1)) * 100);
                  return (
                    <div key={cat} className="space-y-1">
                      <div className="flex justify-between text-xs font-semibold">
                        <span className="capitalize text-slate-300 flex items-center gap-1.5">
                          {getPiiIcon(cat)} {cat.replace('_', ' ')}
                        </span>
                        <span className="text-slate-400">{val} ({percentage}%)</span>
                      </div>
                      <div className="h-2 bg-slate-950 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full" 
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <div className="mt-8 border-t border-white/5 pt-4 flex items-center justify-between text-xs text-slate-400 bg-slate-950/20 p-3 rounded-xl">
            <span>Scan Engine: Heuristic & Regex Rules</span>
            <span className="font-bold text-indigo-400 uppercase tracking-widest text-[9px] bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-0.5 rounded-full">Active</span>
          </div>
        </div>

        {/* Right Columns: Incident Table */}
        <div className="lg:col-span-2 bg-slate-900/40 border border-white/5 rounded-2xl p-6 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-sm font-bold text-slate-200">Recent Violations Log</h3>
              <p className="text-[10px] text-slate-500 uppercase font-black tracking-wider">Audit Trail & Mitigation Action</p>
            </div>
          </div>

          <div className="flex-1 overflow-x-auto min-h-[300px]">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/5 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                  <th className="pb-3 pr-4">Tenant ID</th>
                  <th className="pb-3 pr-4">Direction</th>
                  <th className="pb-3 pr-4">Finding Type</th>
                  <th className="pb-3 pr-4">Action Taken</th>
                  <th className="pb-3 pr-4">Time</th>
                  <th className="pb-3 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-xs text-slate-300">
                {violations.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-600">
                      No security incidents logged. Deploy workflows to begin monitoring.
                    </td>
                  </tr>
                ) : (
                  violations.map((v) => (
                    <tr key={v.id} className="hover:bg-white/[0.01] transition-colors">
                      <td className="py-3.5 pr-4 font-semibold text-slate-200">{v.tenant_id}</td>
                      <td className="py-3.5 pr-4">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          v.direction === 'ingress' ? 'text-sky-400 bg-sky-500/10' : 'text-purple-400 bg-purple-500/10'
                        }`}>
                          {v.direction === 'ingress' ? 'Prompt' : 'Response'}
                        </span>
                      </td>
                      <td className="py-3.5 pr-4">
                        <div className="flex flex-wrap gap-1.5">
                          {v.findings.map((f, idx) => (
                            <span key={idx} className="bg-slate-950 px-2 py-0.5 border border-white/5 rounded text-[10px] text-slate-400 flex items-center gap-1 font-mono uppercase">
                              {f.type}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3.5 pr-4">{getActionBadge(v.action_taken)}</td>
                      <td className="py-3.5 pr-4 text-slate-500 font-mono text-[10px]">
                        {new Date(v.created_at).toLocaleTimeString()}
                      </td>
                      <td className="py-3.5 text-right">
                        <button 
                          onClick={() => setSelectedViolation(v)}
                          className="px-3 py-1 bg-white/5 border border-white/5 hover:bg-white/10 hover:border-white/10 text-slate-300 hover:text-white rounded-lg text-[10px] font-bold transition-all"
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>

      {/* Inspect Dialog / Modal */}
      {selectedViolation && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="relative w-full max-w-2xl bg-slate-900 border border-white/10 rounded-2xl shadow-2xl p-6 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-bold text-slate-100">DLP Violation Details</h2>
              <button 
                onClick={() => setSelectedViolation(null)}
                className="px-3 py-1 hover:bg-white/5 rounded text-xs text-slate-400 hover:text-white transition-colors"
              >
                Close
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4 bg-slate-950/40 p-4 rounded-xl border border-white/5 font-mono">
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-bold block">Incident ID</span>
                  <span className="text-slate-300 mt-1 block">{selectedViolation.id}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-bold block">Run ID</span>
                  <span className="text-slate-300 mt-1 block">{selectedViolation.run_id || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-bold block">Tenant ID</span>
                  <span className="text-slate-300 mt-1 block">{selectedViolation.tenant_id}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-bold block">Timestamp</span>
                  <span className="text-slate-300 mt-1 block">{new Date(selectedViolation.created_at).toLocaleString()}</span>
                </div>
              </div>

              <div>
                <span className="text-slate-400 text-xs font-bold block mb-2">Leaks Findings Details</span>
                <div className="space-y-3">
                  {selectedViolation.findings.map((f, idx) => (
                    <div key={idx} className="p-3 bg-slate-950/60 border border-white/5 rounded-xl flex items-center justify-between gap-4 font-mono">
                      <div className="flex items-center gap-2">
                        {getPiiIcon(f.type)}
                        <div>
                          <span className="text-slate-200 capitalize font-bold">{f.type.replace('_', ' ')}</span>
                          <span className="text-slate-500 text-[10px] ml-3">Match indices: [{f.start}:{f.end}]</span>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="text-slate-300 bg-slate-900 border border-white/5 px-2 py-0.5 rounded text-[11px] font-bold">
                          {f.value}
                        </span>
                        <span className="text-[10px] text-slate-500 block mt-1">Scanner: {f.method}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-8 pt-4 border-t border-white/5 flex items-center justify-between bg-slate-950/20 p-3 rounded-xl">
              <span className="text-xs text-slate-400">Scan Action Applied</span>
              {getActionBadge(selectedViolation.action_taken)}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
