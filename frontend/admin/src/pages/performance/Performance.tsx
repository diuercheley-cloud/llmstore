import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/card'
import { Badge } from '../../components/badge'
import { Button } from '../../components/button'
import { Input } from '../../components/input'
import api from '../../lib/api'
import { 
  Zap, 
  Cpu, 
  BarChart3, 
  AlertTriangle, 
  Activity,
  Play
} from 'lucide-react'

export default function Performance() {
  const [backends, setBackends] = useState<any[]>([])
  const [recommendations, setRecommendations] = useState<any[]>([])
  const [simResult, setSimResult] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [simParams, setSimResultParams] = useState({
    concurrent_requests: 10,
    avg_prompt_tokens: 512,
    avg_completion_tokens: 128
  })

  const fetchData = async () => {
    setLoading(true)
    try {
      // Note: Need to add these to api.ts if not there
      const [b, r] = await Promise.all([
        (api as any).listBackendPerformance(),
        (api as any).getPerformanceRecommendations()
      ])
      setBackends(b)
      setRecommendations(r)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSimulate = async () => {
    try {
      const res = await (api as any).simulatePerformance({
        ...simParams,
        models: ["llama-3-70b"]
      })
      setSimResult(res)
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Performance & Tuning</h1>
          <p className="text-muted-foreground">Otimização de inferência, PagedAttention e scheduling de GPU</p>
        </div>
        <Button onClick={fetchData} variant="outline">
          <Activity className="w-4 h-4 mr-2" /> Atualizar Status
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Cpu className="w-5 h-5" /> Backends & Capabilities
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {backends.map((b) => (
                  <div key={b.backend_id} className="p-4 border rounded-xl bg-muted/30">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="font-bold">{b.backend_id}</h3>
                        <p className="text-xs text-muted-foreground">{b.backend_type.toUpperCase()} • {b.active_models.join(', ')}</p>
                      </div>
                      <Badge>{b.throughput_tokens_sec} tok/s</Badge>
                    </div>
                    
                    <div className="flex flex-wrap gap-2">
                      {b.gpu_resources[0].capabilities.map((c: string) => (
                        <Badge key={c} variant="secondary" className="text-[10px]">
                          {c.replace('_', ' ')}
                        </Badge>
                      ))}
                    </div>

                    <div className="mt-4 grid grid-cols-3 gap-4 text-center">
                      <div className="p-2 bg-background rounded-lg border">
                        <p className="text-[10px] text-muted-foreground uppercase">VRAM Usage</p>
                        <p className="text-sm font-bold">{b.gpu_resources[0].used_vram_gb} / {b.gpu_resources[0].total_vram_gb} GB</p>
                      </div>
                      <div className="p-2 bg-background rounded-lg border">
                        <p className="text-[10px] text-muted-foreground uppercase">Latency P50</p>
                        <p className="text-sm font-bold">{b.latency_ms_p50} ms</p>
                      </div>
                      <div className="p-2 bg-background rounded-lg border">
                        <p className="text-[10px] text-muted-foreground uppercase">Batch Size</p>
                        <p className="text-sm font-bold">max {b.max_batch_size}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <BarChart3 className="w-5 h-5" /> Simulador de Carga
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-medium">Reqs Simultâneos</label>
                  <Input 
                    type="number" 
                    value={simParams.concurrent_requests}
                    onChange={e => setSimResultParams({...simParams, concurrent_requests: parseInt(e.target.value)})}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Prompt Tokens</label>
                  <Input 
                    type="number" 
                    value={simParams.avg_prompt_tokens}
                    onChange={e => setSimResultParams({...simParams, avg_prompt_tokens: parseInt(e.target.value)})}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Gen Tokens</label>
                  <Input 
                    type="number" 
                    value={simParams.avg_completion_tokens}
                    onChange={e => setSimResultParams({...simParams, avg_completion_tokens: parseInt(e.target.value)})}
                  />
                </div>
              </div>
              <Button onClick={handleSimulate} className="w-full">
                <Play className="w-4 h-4 mr-2" /> Rodar Simulação
              </Button>

              {simResult && (
                <div className="mt-6 p-4 rounded-xl border border-blue-500/20 bg-blue-500/5">
                  <h4 className="font-bold text-blue-400 mb-2">Resultado da Predição</h4>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <p className="text-xs text-muted-foreground">Throughput Previsto</p>
                      <p className="text-xl font-bold">{simResult.overall_throughput} tok/s</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Latência Média</p>
                      <p className="text-xl font-bold">{simResult.avg_latency_ms.toFixed(2)} ms</p>
                    </div>
                  </div>
                  {simResult.bottlenecks.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs font-bold text-orange-400 uppercase">Gargalos Identificados:</p>
                      {simResult.bottlenecks.map((b: string, i: number) => (
                        <div key={i} className="flex items-center gap-2 text-sm">
                          <AlertTriangle className="w-4 h-4 text-orange-400" />
                          {b}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="border-green-500/20 bg-green-500/5">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 text-green-400">
                <Zap className="w-5 h-5" /> Recomendações
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {recommendations.map((r) => (
                <div key={r.id} className="p-3 border rounded-lg bg-background/50 space-y-2">
                  <div className="flex justify-between items-center">
                    <h4 className="font-bold text-sm">{r.title}</h4>
                    <Badge variant={r.priority === 'high' ? 'destructive' : 'secondary'}>
                      {r.impact} impact
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">{r.description}</p>
                  <div className="pt-2">
                    <pre className="text-[10px] p-2 bg-muted rounded overflow-x-auto">
                      {JSON.stringify(r.suggested_config, null, 2)}
                    </pre>
                  </div>
                  <Button size="sm" variant="outline" className="w-full text-xs">Aplicar Otimização</Button>
                </div>
              ))}
              {recommendations.length === 0 && (
                <p className="text-sm text-center text-muted-foreground py-8">Configuração ideal detectada.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
