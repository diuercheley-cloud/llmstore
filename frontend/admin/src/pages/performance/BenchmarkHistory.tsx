import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import { Activity, Clock, Zap, BarChart3, Database, ShieldAlert } from 'lucide-react'

export default function BenchmarkHistory() {
  const { data: benchmarks, isLoading } = useQuery({
    queryKey: ['benchmarks'],
    queryFn: async () => {
      const res = await api.get('/admin/performance/benchmarks')
      return res.data
    }
  })

  if (isLoading) return <div className="p-8">Carregando histórico de benchmarks...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-black text-slate-900 mb-8">Histórico de <span className="text-teal-600">Benchmarks</span></h1>

      <div className="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50/50 text-slate-400 text-[10px] font-black uppercase tracking-widest border-b border-slate-100">
            <tr>
              <th className="px-6 py-4">Modelo / Data</th>
              <th className="px-6 py-4">Tokens/sec</th>
              <th className="px-6 py-4">Latência (p50/p99)</th>
              <th className="px-6 py-4">GPU Pressure</th>
              <th className="px-6 py-4">Cache Hit</th>
              <th className="px-6 py-4">Erro</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {benchmarks?.map((b: any) => (
              <tr key={b.id} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-5">
                  <div className="font-bold text-slate-900">{b.model_id}</div>
                  <div className="text-[10px] text-slate-400 font-mono">{new Date(b.timestamp).toLocaleString()}</div>
                </td>
                <td className="px-6 py-5">
                  <div className="flex items-center gap-2 text-teal-600 font-black">
                    <Zap className="w-3.5 h-3.5" />
                    {b.tokens_per_sec.toFixed(1)}
                  </div>
                </td>
                <td className="px-6 py-5">
                   <div className="text-xs font-bold text-slate-700">{b.latency_p50.toFixed(0)}ms / {b.latency_p99.toFixed(0)}ms</div>
                </td>
                <td className="px-6 py-5">
                  <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${b.gpu_memory_pressure > 0.8 ? 'bg-rose-500' : 'bg-teal-500'}`} 
                      style={{ width: `${b.gpu_memory_pressure * 100}%` }}
                    ></div>
                  </div>
                </td>
                <td className="px-6 py-5 text-xs font-bold text-slate-500">
                  {(b.cache_hit_ratio * 100).toFixed(1)}%
                </td>
                <td className="px-6 py-5">
                  <span className={`text-[10px] font-black ${b.error_rate > 0.01 ? 'text-rose-600' : 'text-green-600'}`}>
                    {(b.error_rate * 100).toFixed(1)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
