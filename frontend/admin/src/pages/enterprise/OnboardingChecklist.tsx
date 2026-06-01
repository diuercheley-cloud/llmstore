import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import api from '../../lib/api'
import { CheckCircle2, Circle, FileText, ChevronRight, ArrowRight, Briefcase } from 'lucide-react'

export default function OnboardingChecklist() {
  const { id } = useParams()
  const queryClient = useQueryClient()

  const { data: projects, isLoading: isProjectsLoading } = useQuery({
    queryKey: ['enterprise-projects'],
    queryFn: async () => {
      const res = await api.get('/admin/enterprise/onboarding/projects')
      return res.data
    },
    enabled: !id,
  })

  const { data: project, isLoading } = useQuery({
    queryKey: ['enterprise-project', id],
    queryFn: async () => {
      const res = await api.get(`/admin/enterprise/onboarding/projects/${id}`)
      return res.data
    },
    enabled: Boolean(id),
  })

  const updateTaskMutation = useMutation({
    mutationFn: async ({ taskId, status }: { taskId: string, status: string }) => {
      return api.patch(`/admin/enterprise/onboarding/tasks/${taskId}`, { status })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['enterprise-project', id] })
    }
  })

  const handoverMutation = useMutation({
    mutationFn: async () => {
      return api.post(`/admin/enterprise/onboarding/projects/${id}/handover-report`)
    },
    onSuccess: () => {
      alert('Handover Report gerado com sucesso!')
    }
  })

  if (!id) {
    if (isProjectsLoading) return <div className="p-8">Carregando projetos enterprise...</div>

    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <header className="mb-8">
          <h1 className="text-3xl font-black text-foreground mb-2">Enterprise Checklist</h1>
          <p className="text-muted-foreground font-medium">
            Selecione um projeto para abrir o checklist. Os modelos de acceptance checks e training sessions existem no backend, mas ainda não têm tela própria.
          </p>
        </header>

        <div className="grid gap-4 md:grid-cols-2">
          {projects?.map((p: any) => (
            <Link
              key={p.id}
              to={`/enterprise/checklist/${p.id}`}
              className="bg-card border border-border rounded-3xl p-6 hover:border-accent hover:shadow-xl hover:shadow-blue-500/5 transition-all group"
            >
              <div className="flex items-start justify-between gap-4 mb-4">
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
              <div className="flex items-center justify-between text-accent">
                <span className="text-xs font-black uppercase tracking-widest">Abrir checklist</span>
                <ArrowRight className="w-4 h-4" />
              </div>
            </Link>
          ))}

          {projects?.length === 0 && (
            <div className="md:col-span-2 p-16 text-center bg-secondary border-2 border-dashed border-border rounded-3xl">
              <h3 className="font-bold text-foreground mb-2">Nenhum projeto encontrado</h3>
              <p className="text-muted-foreground">Crie um projeto em Enterprise Onboarding para acessar o checklist.</p>
            </div>
          )}
        </div>
      </div>
    )
  }

  if (isLoading) return <div className="p-8">Carregando checklist...</div>

  const categories = ['discovery', 'environment', 'security', 'deployment', 'installation', 'validation', 'acceptance', 'training', 'handover', 'support']

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center gap-2 text-muted-foreground text-sm font-bold mb-4">
        <Link to="/enterprise/onboarding" className="hover:text-accent transition-colors">Enterprise Onboarding</Link>
        <ChevronRight className="w-4 h-4" />
        <span className="text-foreground">{project?.name}</span>
      </div>

      <header className="mb-10 flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-black text-foreground mb-2">{project?.name}</h1>
          <p className="text-muted-foreground font-medium">Status Atual: <span className="text-accent font-bold uppercase">{project?.status}</span></p>
        </div>
        <div className="flex gap-3">
           <button 
             onClick={() => handoverMutation.mutate()}
             className="bg-foreground text-background px-6 py-2.5 rounded-2xl font-bold text-sm flex items-center gap-2 hover:bg-foreground transition-colors"
           >
             <FileText className="w-4 h-4" />
             Gerar Handover Pack
           </button>
        </div>
      </header>

      <div className="space-y-4">
        {categories.map((cat) => {
          const tasks = project?.tasks.filter((t: any) => t.category === cat)
          const allDone = tasks?.every((t: any) => t.status === 'completed')
          
          return (
            <div key={cat} className={`bg-card border rounded-3xl overflow-hidden transition-all ${allDone ? 'border-green-100' : 'border-border'}`}>
              <div className={`px-6 py-4 flex items-center justify-between ${allDone ? 'bg-primary/10/50' : 'bg-secondary/50'}`}>
                <h3 className="font-black text-[10px] uppercase tracking-widest text-muted-foreground">{cat}</h3>
                {allDone && <CheckCircle2 className="w-4 h-4 text-primary" />}
              </div>
              <div className="divide-y divide-border">
                {tasks?.map((task: any) => (
                  <div key={task.id} className="px-6 py-4 flex items-center justify-between group">
                    <div className="flex items-center gap-4">
                      <button 
                        onClick={() => updateTaskMutation.mutate({ 
                          taskId: task.id, 
                          status: task.status === 'completed' ? 'pending' : 'completed' 
                        })}
                        className={`transition-colors ${task.status === 'completed' ? 'text-primary' : 'text-muted-foreground hover:text-accent'}`}
                      >
                        {task.status === 'completed' ? <CheckCircle2 className="w-6 h-6" /> : <Circle className="w-6 h-6" />}
                      </button>
                      <span className={`font-bold ${task.status === 'completed' ? 'text-muted-foreground line-through' : 'text-foreground'}`}>
                        {task.title}
                      </span>
                    </div>
                    {task.status === 'completed' && (
                      <span className="text-[10px] font-mono text-muted-foreground">
                        Concluído em {new Date(task.completed_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
