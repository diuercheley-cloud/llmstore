import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend, ResponsiveContainer } from 'recharts';
import { Clock } from 'lucide-react';

interface LatencyPoint {
  period: string;
  p50_latency_seconds: number;
  p95_latency_seconds: number;
  p99_latency_seconds: number;
  run_count: number;
}

interface LatencyPercentilesChartProps {
  data: LatencyPoint[];
  granularity: string;
}

export const LatencyPercentilesChart: React.FC<LatencyPercentilesChartProps> = ({ data, granularity }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-slate-900/40 rounded-xl border border-slate-800 text-slate-400 h-80">
        <Clock className="w-8 h-8 mb-2 opacity-50 text-sky-400" />
        <p className="text-sm italic">No latency trend data available for this selection.</p>
      </div>
    );
  }

  const formatSeconds = (val: number) => `${val.toFixed(1)}s`;

  return (
    <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl shadow-2xl backdrop-blur-md p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-semibold text-slate-200 flex items-center gap-2">
          <Clock className="w-4 h-4 text-sky-400" />
          Latency Percentiles (p50 / p95 / p99)
        </h3>
        <span className="text-xs font-semibold text-sky-400 bg-sky-500/10 px-2.5 py-1 rounded-full border border-sky-500/20 capitalize">
          {granularity}
        </span>
      </div>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
              tickFormatter={formatSeconds}
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
              formatter={(value: any, name: any) => [formatSeconds(Number(value)), name]}
              labelFormatter={(label) => `Period: ${label}`}
            />
            <Legend 
              wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
              iconType="circle"
            />
            <Line 
              type="monotone" 
              dataKey="p50_latency_seconds" 
              name="p50 (Median)" 
              stroke="#38bdf8" 
              strokeWidth={2} 
              dot={false} 
              activeDot={{ r: 4 }} 
            />
            <Line 
              type="monotone" 
              dataKey="p95_latency_seconds" 
              name="p95 Percentile" 
              stroke="#f59e0b" 
              strokeWidth={2} 
              dot={false} 
              activeDot={{ r: 4 }} 
            />
            <Line 
              type="monotone" 
              dataKey="p99_latency_seconds" 
              name="p99 Percentile" 
              stroke="#ef4444" 
              strokeWidth={2} 
              dot={false} 
              activeDot={{ r: 4 }} 
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
