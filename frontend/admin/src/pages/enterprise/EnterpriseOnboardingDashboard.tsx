import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import { Briefcase, Users, CheckCircle2, Clock, ArrowRight, Plus } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function EnterpriseOnboardingDashboard() {
  const { data: projects, isLoading } = useQuery({
    queryKey: ['enterprise-projects'],
    queryFn: async () => {
      const res = await api.get('/admin/enterprise/onboarding/projects')
      return res.data
    }
  })

  if (isLoading) return <div className="p-8">Carregando projetos enterprise...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Enterprise <span className="text-accent">Onboarding</span></h1>
          <p className="text-muted-foreground font-medium">Gestão de pilotos e ativação de clientes enterprise.</p>
        </div>
        <button className="bg-accent text-white px-6 py-2.5 rounded-2xl font-bold text-sm flex items-center gap-2 hover:bg-accent/90 transition-colors">
          <Plus className="w-4 h-4" />
          Novo Projeto
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {projects?.map((p: any) => (
          <Link 
            key={p.id} 
            to={`/enterprise/onboarding/${p.id}`}
            className="bg-card border border-border rounded-3xl p-6 hover:border-accent hover:shadow-xl hover:shadow-blue-500/5 transition-all group"
          >
            <div className="flex justify-between items-start mb-4">
              <div className="p-3 bg-accent/10 text-accent rounded-2xl">
                <Briefcase className="w-6 h-6" />
              </div>
              <span className={`px-2 py-1 rounded text-[10px] font-black uppercase tracking-tighter ${
                p.status === 'handed_over' ? 'bg-primary/20 text-primary' : 'bg-accent/20 text-blue-700'
              }`}>
                {p.status.replace(/_/g, ' ')}
              </span>
            </div>
            <h3 className="text-xl font-bold text-foreground mb-1 group-hover:text-accent transition-colors">{p.name}</h3>
            <p className="text-sm text-muted-foreground mb-6 font-medium">Iniciado em {new Date(p.start_date).toLocaleDateString()}</p>
            
            <div className="space-y-3 mb-8">
              <div className="flex justify-between text-[10px] font-black uppercase text-muted-foreground">
                <span>Progresso Técnico</span>
                <span>65%</span>
              </div>
              <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
                <div className="bg-accent/100 h-full w-[65%]"></div>
              </div>
            </div>

            <div className="flex items-center justify-between text-accent">
              <span className="text-xs font-black uppercase tracking-widest">Ver Checklist</span>
              <ArrowRight className="w-4 h-4" />
            </div>
          </Link>
        ))}

        {projects?.length === 0 && (
          <div className="lg:col-span-3 p-20 text-center bg-secondary border-2 border-dashed border-border rounded-3xl">
            <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="font-bold text-foreground">Nenhum projeto ativo</h3>
            <p className="text-muted-foreground">Comece criando um novo piloto para um cliente enterprise.</p>
          </div>
        )}
      </div>
    </div>
  )
}
