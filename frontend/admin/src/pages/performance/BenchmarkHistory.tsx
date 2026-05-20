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
      <h1 className="text-3xl font-black text-foreground mb-8">Histórico de <span className="text-primary">Benchmarks</span></h1>

      <div className="bg-card border border-border rounded-3xl shadow-sm overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-secondary/50 text-muted-foreground text-[10px] font-black uppercase tracking-widest border-b border-border">
            <tr>
              <th className="px-6 py-4">Modelo / Data</th>
              <th className="px-6 py-4">Tokens/sec</th>
              <th className="px-6 py-4">Latência (p50/p99)</th>
              <th className="px-6 py-4">GPU Pressure</th>
              <th className="px-6 py-4">Cache Hit</th>
              <th className="px-6 py-4">Erro</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {benchmarks?.map((b: any) => (
              <tr key={b.id} className="hover:bg-secondary/50 transition-colors">
                <td className="px-6 py-5">
                  <div className="font-bold text-foreground">{b.model_id}</div>
                  <div className="text-[10px] text-muted-foreground font-mono">{new Date(b.timestamp).toLocaleString()}</div>
                </td>
                <td className="px-6 py-5">
                  <div className="flex items-center gap-2 text-primary font-black">
                    <Zap className="w-3.5 h-3.5" />
                    {b.tokens_per_sec.toFixed(1)}
                  </div>
                </td>
                <td className="px-6 py-5">
                   <div className="text-xs font-bold text-foreground">{b.latency_p50.toFixed(0)}ms / {b.latency_p99.toFixed(0)}ms</div>
                </td>
                <td className="px-6 py-5">
                  <div className="w-24 h-1.5 bg-secondary rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${b.gpu_memory_pressure > 0.8 ? 'bg-destructive' : 'bg-primary'}`} 
                      style={{ width: `${b.gpu_memory_pressure * 100}%` }}
                    ></div>
                  </div>
                </td>
                <td className="px-6 py-5 text-xs font-bold text-muted-foreground">
                  {(b.cache_hit_ratio * 100).toFixed(1)}%
                </td>
                <td className="px-6 py-5">
                  <span className={`text-[10px] font-black ${b.error_rate > 0.01 ? 'text-destructive' : 'text-primary'}`}>
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
