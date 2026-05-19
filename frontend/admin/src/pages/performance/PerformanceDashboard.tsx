import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import HealthCard from '../../components/operations/HealthCard'
import ActionPanel from '../../components/operations/ActionPanel'
import { Zap, Gauge, TrendingUp, AlertCircle, RefreshCw, Layers } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useState } from 'react'

export default function PerformanceDashboard() {
  const queryClient = useQueryClient()
  const [isBenchmarking, setIsBenchmarking] = useState(false)

  const { data: currentProfile } = useQuery({
    queryKey: ['current-profile'],
    queryFn: async () => {
      const res = await api.get('/admin/performance/current-profile')
      return res.data
    }
  })

  const { data: recommendations } = useQuery({
    queryKey: ['performance-recommendations'],
    queryFn: async () => {
      const res = await api.get('/admin/performance/recommendations')
      return res.data
    }
  })

  const { data: benchmarks } = useQuery({
    queryKey: ['benchmarks'],
    queryFn: async () => {
      const res = await api.get('/admin/performance/benchmarks')
      return res.data
    }
  })

  const benchmarkMutation = useMutation({
    mutationFn: async (modelId: string) => {
      setIsBenchmarking(true)
      return api.post(`/admin/performance/benchmark?model_id=${modelId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmarks'] })
      queryClient.invalidateQueries({ queryKey: ['performance-recommendations'] })
      setIsBenchmarking(false)
    }
  })

  const lastBenchmark = benchmarks?.[0]

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Performance <span className="text-teal-600">Tuning</span></h1>
          <p className="text-slate-500 font-medium">Otimização de runtime baseada em benchmarks e IA.</p>
        </div>
        <div className="flex gap-3">
           <button 
             onClick={() => benchmarkMutation.mutate('unsloth/gemma-4-E4B-it-GGUF')}
             disabled={isBenchmarking}
             className="bg-slate-900 text-white px-6 py-2.5 rounded-2xl font-bold text-sm flex items-center gap-2 hover:bg-slate-800 transition-colors disabled:opacity-50"
           >
             <RefreshCw className={`w-4 h-4 ${isBenchmarking ? 'animate-spin' : ''}`} />
             {isBenchmarking ? 'Executando Benchmark...' : 'Novo Benchmark'}
           </button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <HealthCard 
          title="Tokens/sec (Last)" 
          value={lastBenchmark?.tokens_per_sec?.toFixed(1) || '0'} 
          icon={<Zap className="w-6 h-6" />}
          description="Velocidade de geração do último teste."
        />
        <HealthCard 
          title="Latência p95" 
          value={`${lastBenchmark?.latency_p95?.toFixed(0) || '0'}ms`} 
          status={lastBenchmark?.latency_p95 > 1000 ? 'warning' : 'healthy'}
          icon={<Gauge className="w-6 h-6" />}
          description="Tempo de resposta do último teste."
        />
        <HealthCard 
          title="Fila Média" 
          value={`${lastBenchmark?.queue_wait_ms?.toFixed(0) || '0'}ms`} 
          icon={<Layers className="w-6 h-6" />}
          description="Tempo de espera em buffer."
        />
        <HealthCard 
          title="Perfil Ativo" 
          value={currentProfile?.name?.toUpperCase() || 'BALANCED'} 
          icon={<TrendingUp className="w-6 h-6" />}
          description="Estratégia de runtime atual."
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {benchmarks && benchmarks.length >= 2 && (
            <div className="bg-slate-900 text-white rounded-3xl p-8 shadow-xl">
              <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                <TrendingUp className="w-6 h-6 text-teal-400" />
                Comparativo: Últimas 2 Execuções
              </h3>
              <div className="grid grid-cols-2 gap-10">
                <div>
                  <div className="text-[10px] font-black text-slate-500 uppercase mb-4 tracking-widest">Atual ({new Date(benchmarks[0].timestamp).toLocaleTimeString()})</div>
                  <div className="space-y-4">
                    <div className="flex justify-between items-end border-b border-slate-800 pb-2">
                      <span className="text-xs font-bold text-slate-400">TPS</span>
                      <span className="text-2xl font-black text-teal-400">{benchmarks[0].tokens_per_sec.toFixed(1)}</span>
                    </div>
                    <div className="flex justify-between items-end border-b border-slate-800 pb-2">
                      <span className="text-xs font-bold text-slate-400">Latency p95</span>
                      <span className="text-2xl font-black text-white">{benchmarks[0].latency_p95.toFixed(0)}ms</span>
                    </div>
                  </div>
                </div>
                <div>
                  <div className="text-[10px] font-black text-slate-500 uppercase mb-4 tracking-widest">Anterior ({new Date(benchmarks[1].timestamp).toLocaleTimeString()})</div>
                  <div className="space-y-4">
                    <div className="flex justify-between items-end border-b border-slate-800 pb-2">
                      <span className="text-xs font-bold text-slate-400">TPS</span>
                      <span className="text-2xl font-black text-slate-500">{benchmarks[1].tokens_per_sec.toFixed(1)}</span>
                    </div>
                    <div className="flex justify-between items-end border-b border-slate-800 pb-2">
                      <span className="text-xs font-bold text-slate-400">Latency p95</span>
                      <span className="text-2xl font-black text-slate-500">{benchmarks[1].latency_p95.toFixed(0)}ms</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="mt-8 pt-6 border-t border-slate-800 flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400">Delta de Performance</span>
                <span className={`text-sm font-black ${benchmarks[0].tokens_per_sec > benchmarks[1].tokens_per_sec ? 'text-green-400' : 'text-rose-400'}`}>
                  {((benchmarks[0].tokens_per_sec / benchmarks[1].tokens_per_sec - 1) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          )}

          <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h3 className="font-black text-slate-900 uppercase tracking-tight">Recomendações de Tuning</h3>
              <TrendingUp className="w-5 h-5 text-teal-600" />
            </div>
            <div className="divide-y divide-slate-100">
              {recommendations?.length === 0 ? (
                <div className="p-10 text-center text-slate-400 font-medium">Nenhuma recomendação no momento. Execute um benchmark para gerar novos insights.</div>
              ) : recommendations?.map((rec: any) => (
                <div key={rec.id} className="p-6 hover:bg-slate-50/50 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <AlertCircle className={`w-4 h-4 ${rec.priority === 'critical' ? 'text-rose-500' : 'text-amber-500'}`} />
                      <h4 className="font-bold text-slate-900">{rec.title}</h4>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${rec.impact === 'PERFORMANCE' ? 'bg-teal-100 text-teal-700' : 'bg-amber-100 text-amber-700'}`}>
                      {rec.impact}
                    </span>
                  </div>
                  <p className="text-sm text-slate-500 mb-4">{rec.description}</p>
                  <div className="flex items-center justify-between">
                     <code className="text-[10px] bg-slate-100 px-2 py-1 rounded font-mono text-slate-600">
                       {JSON.stringify(rec.suggested_config)}
                     </code>
                     <button className="text-xs font-black text-teal-600 hover:text-teal-700 uppercase tracking-widest">
                       Aplicar Sugestão
                     </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <ActionPanel title="Perfis de Runtime" description="Selecione uma estratégia pré-definida.">
            <Link to="/performance/profiles" className="w-full text-center bg-slate-900 text-white font-bold py-3 rounded-2xl hover:bg-slate-800 transition-colors">
              Gerenciar Perfis
            </Link>
          </ActionPanel>

          <div className="bg-slate-50 border border-slate-200 rounded-3xl p-6">
            <h3 className="font-black text-slate-900 uppercase tracking-tight mb-4">Quick Stats</h3>
            <div className="space-y-4">
               <div className="flex justify-between items-center">
                 <span className="text-xs font-bold text-slate-500 uppercase">Total Benchmarks</span>
                 <span className="font-mono font-bold text-slate-900">{benchmarks?.length || 0}</span>
               </div>
               <div className="flex justify-between items-center">
                 <span className="text-xs font-bold text-slate-500 uppercase">Avg TPS</span>
                 <span className="font-mono font-bold text-slate-900">42.5</span>
               </div>
               <div className="flex justify-between items-center">
                 <span className="text-xs font-bold text-slate-500 uppercase">Optimal Profile</span>
                 <span className="text-xs font-black text-teal-600">LOW_LATENCY</span>
               </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
