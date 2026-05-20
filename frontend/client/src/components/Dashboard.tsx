import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  { name: 'Mon', tokens: 4000, cost: 2.4 },
  { name: 'Tue', tokens: 3000, cost: 1.8 },
  { name: 'Wed', tokens: 5000, cost: 3.0 },
  { name: 'Thu', tokens: 2780, cost: 1.6 },
  { name: 'Fri', tokens: 8900, cost: 5.3 },
  { name: 'Sat', tokens: 2390, cost: 1.4 },
  { name: 'Sun', tokens: 3490, cost: 2.1 },
];

export const Dashboard = () => {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Dashboard</h1>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
        <div className="card bg-gradient-to-br from-white to-slate-50">
          <div className="text-slate-500 text-sm font-medium">Total Tokens (This Month)</div>
          <div className="text-2xl md:text-3xl font-bold mt-1 text-slate-900">29,560</div>
        </div>
        <div className="card bg-gradient-to-br from-white to-slate-50">
          <div className="text-slate-500 text-sm font-medium">Accumulated Cost</div>
          <div className="text-2xl md:text-3xl font-bold mt-1 text-slate-900">$17.60</div>
        </div>
        <div className="card bg-gradient-to-br from-white to-slate-50">
          <div className="text-slate-500 text-sm font-medium">Projected Cost</div>
          <div className="text-2xl md:text-3xl font-bold mt-1 text-primary">$32.50</div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-6">Token Usage & Cost</h2>
        <div className="h-[300px] md:h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis 
                dataKey="name" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fill: '#64748b', fontSize: 12 }} 
                dy={10}
              />
              <YAxis 
                yAxisId="left" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fill: '#64748b', fontSize: 12 }} 
              />
              <YAxis 
                yAxisId="right" 
                orientation="right" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fill: '#10b981', fontSize: 12 }} 
              />
              <Tooltip 
                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
              />
              <Line 
                yAxisId="left" 
                type="monotone" 
                dataKey="tokens" 
                stroke="var(--primary-color)" 
                strokeWidth={3} 
                dot={{ r: 4, fill: 'var(--primary-color)' }} 
                activeDot={{ r: 6 }} 
              />
              <Line 
                yAxisId="right" 
                type="monotone" 
                dataKey="cost" 
                stroke="#10b981" 
                strokeWidth={3} 
                dot={{ r: 4, fill: '#10b981' }} 
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
