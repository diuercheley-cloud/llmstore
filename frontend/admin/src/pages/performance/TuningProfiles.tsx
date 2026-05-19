import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { Check, Info, AlertTriangle } from 'lucide-react'
import { useState } from 'react'

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
      alert(`Perfil aplicado: ${data.data.profile}${data.data.advisory ? ' (MODO ADVISORY)' : ''}`)
    }
  })

  if (isLoading) return <div className="p-8">Carregando perfis...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-black text-slate-900 mb-2">Perfis de <span className="text-teal-600">Runtime Tuning</span></h1>
      <p className="text-slate-500 mb-10 font-medium">Configure como o sistema prioriza recursos e responde à carga.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {profiles?.map((p: any) => (
          <div 
            key={p.name} 
            className={`bg-white border-2 rounded-3xl p-6 transition-all cursor-pointer ${p.is_active ? 'border-teal-500 shadow-lg shadow-teal-500/10' : 'border-slate-100 hover:border-slate-300'}`}
            onClick={() => setSelectedProfile(p.name)}
          >
            <div className="flex justify-between items-start mb-4">
              <div className={`p-3 rounded-2xl ${p.is_active ? 'bg-teal-50 text-teal-600' : 'bg-slate-50 text-slate-400'}`}>
                {p.is_active ? <Check className="w-6 h-6" /> : <Info className="w-6 h-6" />}
              </div>
              {p.is_active && (
                <span className="bg-teal-500 text-white text-[10px] font-black px-2 py-1 rounded-full uppercase tracking-tighter">Ativo</span>
              )}
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-1 uppercase tracking-tight">{p.name.replace(/_/g, ' ')}</h3>
            <p className="text-sm text-slate-500 mb-6 h-10 overflow-hidden">{p.description}</p>
            
            <div className="space-y-3 mb-8">
              {Object.entries(p.config).map(([key, val]: [string, any]) => (
                <div key={key} className="flex justify-between text-[10px] font-bold uppercase tracking-wider">
                  <span className="text-slate-400">{key.replace(/_/g, ' ')}</span>
                  <span className="text-slate-700">{val.toString()}</span>
                </div>
              ))}
            </div>

            <button 
              onClick={(e) => {
                e.stopPropagation()
                applyMutation.mutate(p.name)
              }}
              disabled={p.is_active || applyMutation.isPending}
              className={`w-full py-3 rounded-2xl font-bold text-sm transition-all ${p.is_active ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-slate-900 text-white hover:bg-teal-600'}`}
            >
              {p.is_active ? 'Perfil Atual' : 'Aplicar Perfil'}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-12 p-8 bg-amber-50 border border-amber-100 rounded-3xl flex items-start gap-4">
        <AlertTriangle className="w-6 h-6 text-amber-600 shrink-0" />
        <div>
          <h4 className="font-bold text-amber-900 mb-1">Modo de Aplicação de Tuning</h4>
          <p className="text-sm text-amber-700 leading-relaxed">
            Por padrão, a aplicação de perfis é **ADVISORY**. O sistema registra a intenção e os eventos, mas não altera as variáveis de ambiente reais do container. 
            Para permitir mudanças reais, defina <code className="bg-amber-100 px-1 rounded font-bold">RUNTIME_TUNING_APPLY_ENABLED=true</code>.
          </p>
        </div>
      </div>
    </div>
  )
}
