import React from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts';
import { DollarSign } from 'lucide-react';

interface CostPoint {
  period: string;
  total_cost_brl: number;
  run_count: number;
  average_cost_brl: number;
}

interface CostTrendChartProps {
  data: CostPoint[];
  granularity: string;
}

export const CostTrendChart: React.FC<CostTrendChartProps> = ({ data, granularity }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-slate-900/40 rounded-xl border border-slate-800 text-slate-400 h-80">
        <DollarSign className="w-8 h-8 mb-2 opacity-50 text-indigo-400" />
        <p className="text-sm italic">No cost trend data available for this selection.</p>
      </div>
    );
  }

  // Formatting value for YAxis and tooltip
  const formatCurrency = (val: number) => `R$ ${val.toFixed(2)}`;

  return (
    <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl shadow-2xl backdrop-blur-md p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-semibold text-slate-200 flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-indigo-400" />
          Financial & Cost Trend
        </h3>
        <span className="text-xs font-semibold text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20 capitalize">
          {granularity}
        </span>
      </div>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.3} />
            <XAxis 
              dataKey="period" 
              stroke="#64748b" 
              fontSize={11} 
              tickLine={false} 
              axisLine={false} 
            />
            <YAxis 
              stroke="#64748b" 
              fontSize={11} 
              tickLine={false} 
              axisLine={false} 
              tickFormatter={formatCurrency}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#0f172a', 
                borderColor: '#334155', 
                borderRadius: '8px',
                color: '#f8fafc',
                fontSize: '12px',
                fontFamily: 'monospace'
              }}
              formatter={(value: any) => [formatCurrency(Number(value)), 'Total Cost']}
              labelFormatter={(label) => `Period: ${label}`}
            />
            <Area 
              type="monotone" 
              dataKey="total_cost_brl" 
              stroke="#6366f1" 
              strokeWidth={2}
              fillOpacity={1} 
              fill="url(#colorCost)" 
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
