import React, { useState, useEffect } from 'react';
import api from '../../../lib/api';
import { 
  BarChart3, 
  TrendingUp, 
  Clock, 
  DollarSign, 
  Brain, 
  Wrench, 
  ShieldAlert, 
  CheckCircle2, 
  AlertCircle, 
  Calendar,
  Layers,
  Cpu
} from 'lucide-react';
import { CostTrendChart } from './CostTrendChart';
import { LatencyPercentilesChart } from './LatencyPercentilesChart';
import { ToolUsageTable } from './ToolUsageTable';

interface AgentOverview {
  agent_id: string;
  name: string;
  runs: number;
  success_rate: number;
  total_cost_brl: number;
}

export const AgentAnalyticsDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<any>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [agentMetrics, setAgentMetrics] = useState<any>(null);
  const [costTrend, setCostTrend] = useState<any[]>([]);
  const [latencyTrend, setLatencyTrend] = useState<any[]>([]);
  const [toolsUsage, setToolsUsage] = useState<any[]>([]);
  
  const [days, setDays] = useState(30);
  const [granularity, setGranularity] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [error, setError] = useState<string | null>(null);

  // Fetch overview on days change
  useEffect(() => {
    const fetchOverview = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.get(`/api/v1/admin/agents/analytics/overview?days=${days}`);
        setOverview(res.data);
        if (res.data.agents && res.data.agents.length > 0) {
          // If previous selection is not in list, fallback to empty (all agents)
          const exists = res.data.agents.some((a: any) => a.agent_id === selectedAgentId);
          if (!exists) {
            setSelectedAgentId('');
          }
        } else {
          setSelectedAgentId('');
        }
      } catch (err: any) {
        console.error('Failed to load overview analytics:', err);
        setError('Error loading overview analytics data.');
      } finally {
        setLoading(false);
      }
    };
    fetchOverview();
  }, [days]);

  // Fetch specific agent details
  useEffect(() => {
    if (!selectedAgentId) {
      setAgentMetrics(null);
      setCostTrend([]);
      setLatencyTrend([]);
      setToolsUsage([]);
      return;
    }

    const fetchAgentDetails = async () => {
      try {
        const [metricsRes, costRes, latencyRes, toolsRes] = await Promise.all([
          api.get(`/api/v1/admin/agents/analytics/${selectedAgentId}?days=${days}`),
          api.get(`/api/v1/admin/agents/analytics/${selectedAgentId}/costs?days=${days}&granularity=${granularity}`),
          api.get(`/api/v1/admin/agents/analytics/${selectedAgentId}/latency?days=${days}&granularity=${granularity}`),
          api.get(`/api/v1/admin/agents/analytics/${selectedAgentId}/tools?days=${days}`)
        ]);

        setAgentMetrics(metricsRes.data);
        setCostTrend(costRes.data.trend || []);
        setLatencyTrend(latencyRes.data.trend || []);
        setToolsUsage(toolsRes.data.tools || []);
      } catch (err) {
        console.error('Failed to load agent details:', err);
      }
    };

    fetchAgentDetails();
  }, [selectedAgentId, days, granularity]);

  if (loading && !overview) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-950 text-slate-400">
        <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="font-medium animate-pulse">Loading Agentic Analytics...</p>
      </div>
    );
  }

  const activeMetrics = agentMetrics || overview;
  const isAgentMode = !!selectedAgentId;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8 border-b border-slate-900 pb-6">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 via-sky-400 to-emerald-400 bg-clip-text text-transparent flex items-center gap-2">
            <BarChart3 className="w-8 h-8 text-indigo-400" />
            Agentic Analytics
          </h1>
          <p className="text-slate-400 text-sm mt-1">Granular usage, costing, latencies, and tools performance.</p>
        </div>
        
        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Agent Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Agent:</span>
            <select
              value={selectedAgentId}
              onChange={(e) => setSelectedAgentId(e.target.value)}
              className="bg-slate-900 border border-slate-800 text-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow duration-150"
            >
              <option value="">All Agents (Overview)</option>
              {overview?.agents?.map((a: AgentOverview) => (
                <option key={a.agent_id} value={a.agent_id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          {/* Granularity Selector */}
          {isAgentMode && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Trend:</span>
              <select
                value={granularity}
                onChange={(e: any) => setGranularity(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow duration-150"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
          )}

          {/* Timeframe Selector */}
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-slate-500" />
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="bg-slate-900 border border-slate-800 text-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow duration-150"
            >
              <option value={1}>Last 24 Hours</option>
              <option value={7}>Last 7 Days</option>
              <option value={30}>Last 30 Days</option>
              <option value={90}>Last 90 Days</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl mb-6 flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      )}

      {activeMetrics?.status === 'no_data' ? (
        <div className="flex flex-col items-center justify-center p-16 bg-slate-900/20 border border-slate-900 rounded-2xl text-slate-500">
          <BarChart3 className="w-16 h-16 mb-4 stroke-[1.5] text-slate-600 animate-pulse" />
          <h3 className="text-lg font-semibold text-slate-400">No Analytics Data</h3>
          <p className="text-sm mt-1 text-center max-w-sm">There are no agent runs recorded for the selected timeframe. Try selecting a wider timeframe or check back later.</p>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {/* Run Success */}
            <div className="bg-slate-900/40 border border-slate-900 rounded-xl p-6 shadow-xl flex flex-col justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">Success Rate</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-emerald-400">
                    {((activeMetrics?.success_rate || 0) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span className="text-xs text-slate-400">
                  {activeMetrics?.total_runs} runs tracked
                </span>
              </div>
            </div>

            {/* Total Cost */}
            <div className="bg-slate-900/40 border border-slate-900 rounded-xl p-6 shadow-xl flex flex-col justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">Total Cost</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-indigo-400">
                    R$ {(activeMetrics?.total_cost_brl || 0).toFixed(2)}
                  </span>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-indigo-500" />
                <span className="text-xs text-slate-400">
                  {((activeMetrics?.total_tokens || 0) / 1000).toFixed(0)}k total tokens
                </span>
              </div>
            </div>

            {/* Latency */}
            <div className="bg-slate-900/40 border border-slate-900 rounded-xl p-6 shadow-xl flex flex-col justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">
                  {isAgentMode ? 'p50 Latency (Median)' : 'Avg Execution'}
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-sky-400">
                    {isAgentMode 
                      ? `${(activeMetrics?.p50_latency_seconds || 0).toFixed(1)}s` 
                      : 'Active'}
                  </span>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2">
                <Clock className="w-4 h-4 text-sky-500" />
                <span className="text-xs text-slate-400">
                  {isAgentMode ? `p95: ${activeMetrics?.p95_latency_seconds?.toFixed(1)}s` : 'Aggregated per agent'}
                </span>
              </div>
            </div>

            {/* Policy & Security */}
            <div className="bg-slate-900/40 border border-slate-900 rounded-xl p-6 shadow-xl flex flex-col justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">Policy Denials</span>
                <div className="flex items-baseline gap-2">
                  <span className={`text-3xl font-extrabold ${activeMetrics?.policy_denials > 0 ? 'text-rose-400' : 'text-slate-300'}`}>
                    {activeMetrics?.policy_denials || 0}
                  </span>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-500" />
                <span className="text-xs text-slate-400">
                  {activeMetrics?.approval_wait_time_seconds > 0 
                    ? `${(activeMetrics.approval_wait_time_seconds / 60).toFixed(0)}m waiting approval` 
                    : 'No pending approvals'}
                </span>
              </div>
            </div>
          </div>

          {/* Trends & Detailed Charts (Visible in single agent mode) */}
          {isAgentMode ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              <CostTrendChart data={costTrend} granularity={granularity} />
              <LatencyPercentilesChart data={latencyTrend} granularity={granularity} />
            </div>
          ) : (
            /* All Agents Overview Table (Visible in tenant overview mode) */
            <div className="bg-slate-900/40 border border-slate-900 rounded-xl overflow-hidden mb-8">
              <div className="px-6 py-4 border-b border-slate-900/60 bg-slate-950/40 flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                <h3 className="font-semibold text-slate-200">Active Agents Breakdown</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase tracking-wider bg-slate-900/10">
                      <th className="px-6 py-3">Agent Name</th>
                      <th className="px-6 py-3 text-right">Runs Count</th>
                      <th className="px-6 py-3 text-right">Success Rate</th>
                      <th className="px-6 py-3 text-right">Total Cost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-900 text-sm">
                    {overview?.agents?.map((agent: AgentOverview) => (
                      <tr 
                        key={agent.agent_id} 
                        className="hover:bg-slate-900/40 transition-colors duration-150 cursor-pointer"
                        onClick={() => setSelectedAgentId(agent.agent_id)}
                      >
                        <td className="px-6 py-4 font-semibold text-slate-300 flex items-center gap-2">
                          <Cpu className="w-4 h-4 text-sky-400 opacity-60" />
                          {agent.name}
                        </td>
                        <td className="px-6 py-4 text-right text-slate-300 font-mono">
                          {agent.runs}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <span className={`inline-flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded-full font-medium ${
                            agent.success_rate >= 0.9 
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                              : agent.success_rate >= 0.7 
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          }`}>
                            {(agent.success_rate * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right font-mono text-indigo-400 font-semibold">
                          R$ {agent.total_cost_brl.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tool usage table */}
          {isAgentMode && (
            <div className="grid grid-cols-1 gap-8 mb-8">
              <ToolUsageTable tools={toolsUsage} />
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AgentAnalyticsDashboard;
