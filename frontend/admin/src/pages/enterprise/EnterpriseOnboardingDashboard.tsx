import { useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { Briefcase, Users, ArrowRight, Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useState } from 'react'
import { toast } from 'sonner'

export default function EnterpriseOnboardingDashboard() {
  const queryClient = useQueryClient()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [customerName, setCustomerName] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [projectName, setProjectName] = useState('')
  const [tier, setTier] = useState('pilot')

  const { data: projects, isLoading } = useQuery({
    queryKey: ['enterprise-projects'],
    queryFn: async () => {
      return api.listEnterpriseProjects()
    }
  })

  const handleCreateProject = async () => {
    try {
      if (!customerName.trim() || !contactEmail.trim() || !projectName.trim()) {
        toast.error('Preencha nome do cliente, email e nome do projeto')
        return
      }

      await api.createEnterpriseProject({
        customer_name: customerName.trim(),
        contact_email: contactEmail.trim(),
        project_name: projectName.trim(),
        tier,
      })

      toast.success('Projeto criado com sucesso')
      setIsCreateOpen(false)
      setCustomerName('')
      setContactEmail('')
      setProjectName('')
      setTier('pilot')
      await queryClient.invalidateQueries({ queryKey: ['enterprise-projects'] })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Falha ao criar projeto')
    }
  }

  if (isLoading) return <div className="p-8">Carregando projetos enterprise...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">Enterprise <span className="text-accent">Onboarding</span></h1>
          <p className="text-muted-foreground font-medium">Gestão de pilotos e ativação de clientes enterprise.</p>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="bg-accent text-background px-6 py-2.5 rounded-2xl font-bold text-sm flex items-center gap-2 hover:bg-accent/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Novo Projeto
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {projects?.map((p: any) => (
          <Link 
            key={p.id} 
            to={`/enterprise/checklist/${p.id}`}
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

      {isCreateOpen && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-foreground/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-3xl border border-border bg-card shadow-2xl">
            <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
              <div>
                <h2 className="text-xl font-black text-foreground">Novo Projeto</h2>
                <p className="text-sm text-muted-foreground">Cria customer, projeto e tasks iniciais no backend.</p>
              </div>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="rounded-xl border border-border px-3 py-2 text-sm font-bold text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                Fechar
              </button>
            </div>

            <div className="grid gap-4 px-6 py-5 md:grid-cols-2">
              <label className="space-y-2 block md:col-span-1">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Nome do Cliente</span>
                <input
                  value={customerName}
                  onChange={e => setCustomerName(e.target.value)}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                  placeholder="Ex: Acme Corp"
                />
              </label>

              <label className="space-y-2 block md:col-span-1">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Email de Contato</span>
                <input
                  value={contactEmail}
                  onChange={e => setContactEmail(e.target.value)}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                  placeholder="contato@empresa.com"
                />
              </label>

              <label className="space-y-2 block md:col-span-2">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Nome do Projeto</span>
                <input
                  value={projectName}
                  onChange={e => setProjectName(e.target.value)}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                  placeholder="Ex: Piloto IA Brasil"
                />
              </label>

              <label className="space-y-2 block md:col-span-1">
                <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Tier</span>
                <select
                  value={tier}
                  onChange={e => setTier(e.target.value)}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-accent"
                >
                  <option value="pilot">pilot</option>
                  <option value="production">production</option>
                </select>
              </label>
            </div>

            <div className="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
              <button
                onClick={() => setIsCreateOpen(false)}
                className="rounded-2xl border border-border px-4 py-2.5 text-sm font-bold text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                Cancelar
              </button>
              <button
                onClick={handleCreateProject}
                className="rounded-2xl bg-accent px-4 py-2.5 text-sm font-bold text-background hover:bg-accent/90"
              >
                Criar Projeto
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
