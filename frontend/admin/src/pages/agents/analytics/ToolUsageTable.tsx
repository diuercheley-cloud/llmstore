import React from 'react';
import { Wrench, AlertTriangle, Clock } from 'lucide-react';

interface ToolMetric {
  tool_name: string;
  total_calls: number;
  failure_rate: number;
  average_latency_ms: number;
}

interface ToolUsageTableProps {
  tools: ToolMetric[];
}

export const ToolUsageTable: React.FC<ToolUsageTableProps> = ({ tools }) => {
  if (!tools || tools.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-slate-900/40 rounded-xl border border-slate-800 text-slate-400">
        <Wrench className="w-8 h-8 mb-2 opacity-50" />
        <p className="text-sm italic">No tool usage recorded for this timeframe.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden bg-slate-900/60 border border-slate-800/80 rounded-xl shadow-2xl backdrop-blur-md">
      <div className="px-6 py-4 border-b border-slate-800/60 bg-slate-950/40 flex items-center justify-between">
        <h3 className="font-semibold text-slate-200 flex items-center gap-2">
          <Wrench className="w-4 h-4 text-emerald-400" />
          Tool Execution Usage
        </h3>
        <span className="text-xs font-medium text-slate-400 bg-slate-800/50 px-2 py-0.5 rounded-full">
          {tools.length} active tools
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase tracking-wider bg-slate-900/30">
              <th className="px-6 py-3">Tool Name</th>
              <th className="px-6 py-3 text-right">Total Calls</th>
              <th className="px-6 py-3 text-right">Failure Rate</th>
              <th className="px-6 py-3 text-right">Avg Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50 text-sm">
            {tools.map((tool) => (
              <tr key={tool.tool_name} className="hover:bg-slate-800/20 transition-colors duration-150">
                <td className="px-6 py-4 font-mono text-emerald-400 font-medium">
                  {tool.tool_name}
                </td>
                <td className="px-6 py-4 text-right text-slate-300 font-semibold">
                  {tool.total_calls.toLocaleString()}
                </td>
                <td className="px-6 py-4 text-right">
                  <span className={`inline-flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded-full font-medium ${
                    tool.failure_rate > 0.1 
                      ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' 
                      : tool.failure_rate > 0 
                      ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  }`}>
                    {tool.failure_rate > 0 && <AlertTriangle className="w-3 h-3" />}
                    {(tool.failure_rate * 100).toFixed(1)}%
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <span className="inline-flex items-center gap-1 font-mono text-slate-300">
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    {tool.average_latency_ms.toFixed(0)}ms
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
