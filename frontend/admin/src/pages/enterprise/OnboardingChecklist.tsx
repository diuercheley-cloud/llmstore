import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import api from '../../lib/api'
import { CheckCircle2, Circle, AlertCircle, FileText, Download, ChevronRight } from 'lucide-react'

export default function OnboardingChecklist() {
  const { id } = useParams()
  const queryClient = useQueryClient()

  const { data: project, isLoading } = useQuery({
    queryKey: ['enterprise-project', id],
    queryFn: async () => {
      const res = await api.get(`/admin/enterprise/onboarding/projects/${id}`)
      return res.data
    }
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

  if (isLoading) return <div className="p-8">Carregando checklist...</div>

  const categories = ['discovery', 'environment', 'security', 'deployment', 'installation', 'validation', 'acceptance', 'training', 'handover', 'support']

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center gap-2 text-slate-400 text-sm font-bold mb-4">
        <Link to="/enterprise/onboarding" className="hover:text-blue-600 transition-colors">Enterprise Onboarding</Link>
        <ChevronRight className="w-4 h-4" />
        <span className="text-slate-900">{project?.name}</span>
      </div>

      <header className="mb-10 flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-black text-slate-900 mb-2">{project?.name}</h1>
          <p className="text-slate-500 font-medium">Status Atual: <span className="text-blue-600 font-bold uppercase">{project?.status}</span></p>
        </div>
        <div className="flex gap-3">
           <button 
             onClick={() => handoverMutation.mutate()}
             className="bg-slate-900 text-white px-6 py-2.5 rounded-2xl font-bold text-sm flex items-center gap-2 hover:bg-slate-800 transition-colors"
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
            <div key={cat} className={`bg-white border rounded-3xl overflow-hidden transition-all ${allDone ? 'border-green-100' : 'border-slate-200'}`}>
              <div className={`px-6 py-4 flex items-center justify-between ${allDone ? 'bg-green-50/50' : 'bg-slate-50/50'}`}>
                <h3 className="font-black text-[10px] uppercase tracking-widest text-slate-500">{cat}</h3>
                {allDone && <CheckCircle2 className="w-4 h-4 text-green-600" />}
              </div>
              <div className="divide-y divide-slate-100">
                {tasks?.map((task: any) => (
                  <div key={task.id} className="px-6 py-4 flex items-center justify-between group">
                    <div className="flex items-center gap-4">
                      <button 
                        onClick={() => updateTaskMutation.mutate({ 
                          taskId: task.id, 
                          status: task.status === 'completed' ? 'pending' : 'completed' 
                        })}
                        className={`transition-colors ${task.status === 'completed' ? 'text-green-600' : 'text-slate-300 hover:text-blue-600'}`}
                      >
                        {task.status === 'completed' ? <CheckCircle2 className="w-6 h-6" /> : <Circle className="w-6 h-6" />}
                      </button>
                      <span className={`font-bold ${task.status === 'completed' ? 'text-slate-400 line-through' : 'text-slate-700'}`}>
                        {task.title}
                      </span>
                    </div>
                    {task.status === 'completed' && (
                      <span className="text-[10px] font-mono text-slate-400">
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
