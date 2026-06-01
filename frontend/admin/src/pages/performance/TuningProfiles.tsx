import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { Check, Info, AlertTriangle } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

export default function TuningProfiles() {
  const queryClient = useQueryClient()
  const [selectedProfile, setSelectedProfile] = useState<string | null>(null)

  const { data: profiles, isLoading } = useQuery({
    queryKey: ['tuning-profiles'],
    queryFn: async () => {
      const res = await api.get('/admin/performance/profiles')
      return res.data
    }
  })

  const applyMutation = useMutation({
    mutationFn: async (profileName: string) => {
      return api.post(`/admin/performance/apply-profile?profile_name=${profileName}`)
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tuning-profiles'] })
      queryClient.invalidateQueries({ queryKey: ['current-profile'] })
      toast.success(`Perfil aplicado: ${data.data.profile}${data.data.advisory ? ' (MODO ADVISORY)' : ''}`)
    }
  })

  const seedMutation = useMutation({
    mutationFn: async () => api.post('/admin/performance/seed-profiles'),
    onSuccess: () => {
      toast.success('Perfis padrão inicializados')
      queryClient.invalidateQueries({ queryKey: ['tuning-profiles'] })
    },
    onError: () => {
      toast.error('Falha ao inicializar perfis padrão')
    }
  })

  if (isLoading) return <div className="p-8">Carregando perfis...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-black text-foreground mb-2">Perfis de <span className="text-primary">Runtime Tuning</span></h1>
          <p className="text-muted-foreground font-medium">Configure como o sistema prioriza recursos e responde à carga.</p>
        </div>
        <button
          onClick={() => seedMutation.mutate()}
          disabled={seedMutation.isPending}
          className="bg-secondary text-foreground font-bold px-4 py-2.5 rounded-2xl hover:bg-secondary/80 transition-colors disabled:opacity-50"
        >
          {seedMutation.isPending ? 'Inicializando...' : 'Inicializar perfis padrão'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {profiles?.map((p: any) => (
          <div 
            key={p.name} 
            className={`bg-card border-2 rounded-3xl p-6 transition-all cursor-pointer ${p.is_active ? 'border-primary shadow-lg shadow-teal-500/10' : 'border-border hover:border-border'}`}
            onClick={() => setSelectedProfile(p.name)}
          >
            <div className="flex justify-between items-start mb-4">
              <div className={`p-3 rounded-2xl ${p.is_active ? 'bg-primary/10 text-primary' : 'bg-secondary text-muted-foreground'}`}>
                {p.is_active ? <Check className="w-6 h-6" /> : <Info className="w-6 h-6" />}
              </div>
              {p.is_active && (
                <span className="bg-primary text-background text-[10px] font-black px-2 py-1 rounded-full uppercase tracking-tighter">Ativo</span>
              )}
            </div>
            <h3 className="text-xl font-bold text-foreground mb-1 uppercase tracking-tight">{p.name.replace(/_/g, ' ')}</h3>
            <p className="text-sm text-muted-foreground mb-6 h-10 overflow-hidden">{p.description}</p>
            
            <div className="space-y-3 mb-8">
              {Object.entries(p.config).map(([key, val]: [string, any]) => (
                <div key={key} className="flex justify-between text-[10px] font-bold uppercase tracking-wider">
                  <span className="text-muted-foreground">{key.replace(/_/g, ' ')}</span>
                  <span className="text-foreground">{val.toString()}</span>
                </div>
              ))}
            </div>

            <button 
              onClick={(e) => {
                e.stopPropagation()
                applyMutation.mutate(p.name)
              }}
              disabled={p.is_active || applyMutation.isPending}
              className={`w-full py-3 rounded-2xl font-bold text-sm transition-all ${p.is_active ? 'bg-secondary text-muted-foreground cursor-not-allowed' : 'bg-foreground text-background hover:bg-primary'}`}
            >
              {p.is_active ? 'Perfil Atual' : 'Aplicar Perfil'}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-12 p-8 bg-yellow-500/10 border border-amber-100 rounded-3xl flex items-start gap-4">
        <AlertTriangle className="w-6 h-6 text-yellow-600 shrink-0" />
        <div>
          <h4 className="font-bold text-amber-900 mb-1">Modo de Aplicação de Tuning</h4>
          <p className="text-sm text-yellow-600 leading-relaxed">
            Por padrão, a aplicação de perfis é **ADVISORY**. O sistema registra a intenção e os eventos, mas não altera as variáveis de ambiente reais do container. 
            Para permitir mudanças reais, defina <code className="bg-yellow-500/20 px-1 rounded font-bold">RUNTIME_TUNING_APPLY_ENABLED=true</code>.
          </p>
        </div>
      </div>
    </div>
  )
}
