import { AlertCircle } from 'lucide-react'
import Timeline from '../../components/operations/Timeline'

export default function IncidentTimeline() {
  const incidents = [
    {
      id: '1',
      title: 'Latência Elevada em gemma-7b',
      description: 'Investigando aumento de 200ms no processamento de requisições no cluster de São Paulo.',
      timestamp: '2024-05-19 14:20',
      status: 'warning' as const,
    },
    {
      id: '2',
      title: 'Interrupção Parcial no Backend OpenRouter',
      description: 'O provedor OpenRouter está enfrentando instabilidades globais. Roteamento alternativo ativado.',
      timestamp: '2024-05-19 09:15',
      status: 'error' as const,
    },
    {
      id: '3',
      title: 'Manutenção Concluída - Database Upgrade',
      description: 'Migração para PostgreSQL 16 finalizada sem impacto para usuários.',
      timestamp: '2024-05-18 23:00',
      status: 'success' as const,
    },
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-8">
        <AlertCircle className="w-8 h-8 text-rose-500" />
        <h1 className="text-3xl font-black text-slate-900">Incident <span className="text-teal-600">Timeline</span></h1>
      </div>

      <div className="bg-white border border-slate-200 rounded-3xl p-10 shadow-sm">
        <Timeline events={incidents} />
      </div>
    </div>
  )
}
