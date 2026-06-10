import { useQuery, useMutation } from '@tanstack/react-query'
import api from '../../lib/api'
import { Cpu, Server, Activity, FastForward, CheckCircle2, AlertCircle, Terminal, Play, Info } from 'lucide-react'
import { useState } from 'react'
import { AdvancedTable } from '../../components/table/advanced-table'
import { toast } from 'sonner'
import type { ColumnDef } from '@tanstack/react-table'

interface InferenceBackend {
  id: string
  name: string
  provider: string
  backend_url: string
  is_active: boolean
  health: string
  capabilities: string[]
}

export default function InferenceBackends() {
  const [simulationResult, setSimulationResult] = useState<any>(null)

  const { data: backends, isLoading, refetch } = useQuery({
    queryKey: ['inference-backends'],
    queryFn: async () => {
      const res = await api.get('/admin/inference/backends')
      return res.data
    }
  })

  const simulateMutation = useMutation({
    mutationFn: async (payload: { model: string, capability: string }) => {
      const res = await api.post('/admin/inference/routing/simulate', null, {
        params: payload
      })
      return res.data
    },
    onSuccess: (data) => {
      setSimulationResult(data)
      toast.success('Simulação concluída')
    },
    onError: () => {
      toast.error('Falha na simulação')
    }
  })

  const columns: ColumnDef<InferenceBackend>[] = [
    {
      accessorKey: 'name',
      header: 'Backend',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${row.original.is_active ? 'bg-primary/10 text-primary' : 'bg-secondary text-muted-foreground'}`}>
            <Server className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-foreground">{row.original.name}</h3>
            <span className="text-[10px] px-1.5 py-0.5 bg-secondary text-muted-foreground rounded uppercase font-black">
              {row.original.provider}
            </span>
          </div>
        </div>
      )
    },
    {
      accessorKey: 'backend_url',
      header: 'Endpoint',
      cell: ({ row }) => (
        <div className="font-mono text-[10px] text-muted-foreground">
          {row.original.backend_url}
        </div>
      )
    },
    {
      accessorKey: 'health',
      header: 'Health',
      cell: ({ row }) => row.original.health === 'healthy' ? (
        <span className="inline-flex items-center gap-1.5 text-primary text-[10px] font-black uppercase">
          <CheckCircle2 className="w-3.5 h-3.5" /> Healthy
        </span>
      ) : (
        <span className="inline-flex items-center gap-1.5 text-destructive text-[10px] font-black uppercase">
          <AlertCircle className="w-3.5 h-3.5" /> Unhealthy
        </span>
      )
    },
    {
      accessorKey: 'capabilities',
      header: 'Capacidades',
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.capabilities.map(cap => (
            <span key={cap} className="px-1.5 py-0.5 bg-primary/5 text-primary text-[9px] font-bold rounded border border-primary/10">
              {cap}
            </span>
          ))}
        </div>
      )
    }
  ]

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-foreground flex items-center gap-3">
            <FastForward className="w-8 h-8 text-primary" /> INFERENCE BACKENDS
          </h1>
          <p className="text-muted-foreground mt-1">Gestão avançada de abstração de inferência e roteamento inteligente.</p>
        </div>
        <button 
          onClick={() => refetch()}
          className="flex items-center gap-2 px-4 py-2 bg-secondary text-foreground rounded-xl font-bold text-sm hover:bg-secondary/80 transition-all"
        >
          <Activity className="w-4 h-4" /> Atualizar Status
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
            <div className="p-6 border-b border-border flex items-center justify-between">
              <h2 className="font-bold flex items-center gap-2">
                <Cpu className="w-5 h-5 text-primary" /> Backends Disponíveis
              </h2>
            </div>
            <AdvancedTable 
              id="inference-backends"
              columns={columns} 
              data={backends || []} 
              isLoading={isLoading}
            />
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-primary/5 border border-primary/10 rounded-3xl p-6">
            <h2 className="font-bold flex items-center gap-2 mb-4">
              <Play className="w-5 h-5 text-primary" /> Modo Dry-Run / Simulação
            </h2>
            <div className="space-y-4">
              <div>
                <label className="text-[10px] font-black uppercase text-muted-foreground mb-1 block">Modelo para Teste</label>
                <input 
                  type="text" 
                  id="sim-model"
                  placeholder="llama3-8b"
                  className="w-full bg-background border border-border rounded-xl px-4 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-[10px] font-black uppercase text-muted-foreground mb-1 block">Capacidade Requerida</label>
                <select id="sim-cap" className="w-full bg-background border border-border rounded-xl px-4 py-2 text-sm">
                  <option value="chat">Chat</option>
                  <option value="text">Text Completion</option>
                  <option value="embeddings">Embeddings</option>
                </select>
              </div>
              <button 
                onClick={() => {
                  const model = (document.getElementById('sim-model') as HTMLInputElement).value || 'llama3-8b'
                  const capability = (document.getElementById('sim-cap') as HTMLSelectElement).value
                  simulateMutation.mutate({ model, capability })
                }}
                disabled={simulateMutation.isPending}
                className="w-full py-3 bg-primary text-primary-foreground rounded-xl font-black text-sm shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50"
              >
                {simulateMutation.isPending ? 'SIMULANDO...' : 'SIMULAR ROTEAMENTO'}
              </button>
            </div>

            {simulationResult && (
              <div className="mt-6 p-4 bg-background border border-border rounded-2xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase text-muted-foreground">Resultado</span>
                  {simulationResult.selected_backend ? (
                    <span className="text-[10px] font-black uppercase text-primary">SUCESSO</span>
                  ) : (
                    <span className="text-[10px] font-black uppercase text-destructive">FALHA</span>
                  )}
                </div>
                {simulationResult.selected_backend && (
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-primary" />
                    <span className="font-bold text-sm">{simulationResult.selected_backend}</span>
                  </div>
                )}
                <div className="text-[11px] text-muted-foreground leading-relaxed italic">
                  "{simulationResult.reason}"
                </div>
              </div>
            )}
          </div>

          <div className="bg-card border border-border rounded-3xl p-6">
            <h2 className="font-bold flex items-center gap-2 mb-4">
              <Info className="w-5 h-5 text-muted-foreground" /> Info Operacional
            </h2>
            <div className="space-y-3 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Estratégia Atual:</span>
                <span className="font-bold">Priority-based</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Fallback Seguro:</span>
                <span className="font-bold text-primary">ATIVADO</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Detection:</span>
                <span className="font-bold uppercase">Automática</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
