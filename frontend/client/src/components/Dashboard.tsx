import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../lib/api';
import { Loader2, AlertCircle } from 'lucide-react';

export const Dashboard = () => {
  const [usage, setUsage] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [usageData, statsData] = await Promise.all([
          api.getPortalUsage(),
          api.getPortalUsageStats(),
        ]);
        setUsage(usageData);
        setStats(statsData);
      } catch (err: any) {
        setError(err.message || 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-slate-500 font-medium">Carregando dados do dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-100 rounded-2xl p-8 flex flex-col items-center gap-4 text-center">
        <AlertCircle className="w-12 h-12 text-red-500" />
        <div>
          <h3 className="text-lg font-bold text-red-900">Erro ao carregar Dashboard</h3>
          <p className="text-red-700 mt-1">{error}</p>
        </div>
        <button 
          onClick={() => window.location.reload()}
          className="btn bg-red-600 hover:bg-red-700 text-white border-none px-6"
        >
          Tentar Novamente
        </button>
      </div>
    );
  }

  const chartData = stats?.daily_usage?.map((d: any) => ({
    name: new Date(d.day).toLocaleDateString(undefined, { weekday: 'short' }),
    tokens: d.tokens,
    requests: d.requests
  })) || [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Dashboard</h1>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
        <div className="card bg-gradient-to-br from-white to-slate-50">
          <div className="text-slate-500 text-sm font-medium">Tokens Consumed (Month)</div>
          <div className="text-2xl md:text-3xl font-bold mt-1 text-slate-900">
            {usage?.tokens_month?.toLocaleString() || 0}
          </div>
        </div>
        <div className="card bg-gradient-to-br from-white to-slate-50">
          <div className="text-slate-500 text-sm font-medium">Estimated Cost (Month)</div>
          <div className="text-2xl md:text-3xl font-bold mt-1 text-slate-900">
            {usage?.customer_pricing?.currency} {usage?.customer_pricing?.month_amount?.toFixed(2) || '0.00'}
          </div>
        </div>
        <div className="card bg-gradient-to-br from-white to-slate-50">
          <div className="text-slate-500 text-sm font-medium">Total Requests (Month)</div>
          <div className="text-2xl md:text-3xl font-bold mt-1 text-primary">
            {usage?.requests_month?.toLocaleString() || 0}
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-6">Token Usage Trends</h2>
        <div className="h-[300px] md:h-[400px] w-full">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis 
                  dataKey="name" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#64748b', fontSize: 12 }} 
                  dy={10}
                />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#64748b', fontSize: 12 }} 
                />
                <Tooltip 
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="tokens" 
                  stroke="var(--primary-color)" 
                  strokeWidth={3} 
                  dot={{ r: 4, fill: 'var(--primary-color)' }} 
                  activeDot={{ r: 6 }} 
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-400 italic">
              Nenhum dado de uso nos últimos 30 dias.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
