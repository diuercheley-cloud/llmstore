import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { UserCheck, Shield, Key, History, Plus, UserPlus, ShieldAlert, CheckCircle2, Copy } from 'lucide-react'
import { useState } from 'react'
import { Modal } from '../../components/modal'
import { toast } from 'sonner'

function CreateAdminModal({ open, onOpenChange, roles }: { open: boolean, onOpenChange: (open: boolean) => void, roles: any[] }) {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({ username: '', email: '', display_name: '', role_ids: [] as string[] })
  const [issuedToken, setIssuedToken] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (data: any) => api.createRbacUser(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['rbac-users'] })
      setIssuedToken(data.admin_token)
      toast.success('Administrador criado com sucesso!')
    },
    onError: (err: any) => {
      toast.error(err.message || 'Erro ao criar administrador')
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate(formData)
  }

  const handleClose = () => {
    onOpenChange(false)
    setIssuedToken(null)
    setFormData({ username: '', email: '', display_name: '', role_ids: [] })
    mutation.reset()
  }

  if (issuedToken) {
    return (
      <Modal open={open} onOpenChange={handleClose} title="Token Gerado" description="Copie o token abaixo. Ele não será exibido novamente.">
        <div className="space-y-4">
          <div className="p-4 bg-muted rounded-2xl flex items-center justify-between gap-4 font-mono text-sm break-all border border-border">
            <span>{issuedToken}</span>
            <button 
              onClick={() => { navigator.clipboard.writeText(issuedToken); toast.info('Token copiado!') }}
              className="p-2 hover:bg-background rounded-lg transition-colors"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
          <button onClick={handleClose} className="w-full bg-foreground text-background py-3 rounded-2xl font-bold">
            Entendido, fechar
          </button>
        </div>
      </Modal>
    )
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Novo Administrador" description="Crie um novo usuário com acesso administrativo.">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label className="text-xs font-black uppercase tracking-widest text-muted-foreground">Username</label>
          <input 
            className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 outline-none focus:ring-2 focus:ring-primary/50"
            value={formData.username}
            onChange={e => setFormData({ ...formData, username: e.target.value })}
            required
            placeholder="ex: admin_joao"
          />
        </div>
        <div className="space-y-2">
          <label className="text-xs font-black uppercase tracking-widest text-muted-foreground">Nome Completo</label>
          <input 
            className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 outline-none focus:ring-2 focus:ring-primary/50"
            value={formData.display_name}
            onChange={e => setFormData({ ...formData, display_name: e.target.value })}
            required
            placeholder="ex: João Silva"
          />
        </div>
        <div className="space-y-2">
          <label className="text-xs font-black uppercase tracking-widest text-muted-foreground">Email</label>
          <input 
            className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 outline-none focus:ring-2 focus:ring-primary/50"
            type="email"
            value={formData.email}
            onChange={e => setFormData({ ...formData, email: e.target.value })}
            placeholder="ex: joao@empresa.com"
          />
        </div>
        <div className="space-y-2">
          <label className="text-xs font-black uppercase tracking-widest text-muted-foreground">Cargos</label>
          <div className="grid grid-cols-2 gap-2">
            {roles?.map(role => (
              <label key={role.id} className="flex items-center gap-2 p-3 bg-muted rounded-xl cursor-pointer hover:bg-primary/5 transition-colors border border-border">
                <input 
                  type="checkbox"
                  checked={formData.role_ids.includes(role.id)}
                  onChange={e => {
                    const ids = e.target.checked 
                      ? [...formData.role_ids, role.id]
                      : formData.role_ids.filter(id => id !== role.id)
                    setFormData({ ...formData, role_ids: ids })
                  }}
                />
                <span className="text-xs font-bold">{role.name}</span>
              </label>
            ))}
          </div>
        </div>
        <button 
          disabled={mutation.isPending}
          className="w-full bg-primary text-primary-foreground py-3 rounded-2xl font-bold mt-4 hover:opacity-90 transition-all disabled:opacity-50"
        >
          {mutation.isPending ? 'Criando...' : 'Criar Administrador'}
        </button>
      </form>
    </Modal>
  )
}

export default function RbacManagement() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('users')
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)

  const { data: users, isLoading: usersLoading } = useQuery({
    queryKey: ['rbac-users'],
    queryFn: () => api.listRbacUsers()
  })

  const { data: roles, isLoading: rolesLoading } = useQuery({
    queryKey: ['rbac-roles'],
    queryFn: () => api.listRbacRoles()
  })

  const { data: audit, isLoading: auditLoading } = useQuery({
    queryKey: ['rbac-audit'],
    queryFn: () => api.listRbacAudit()
  })

  if (usersLoading || rolesLoading) return <div className="p-8">Carregando RBAC...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight">RBAC <span className="text-primary">Management</span></h1>
          <p className="text-muted-foreground font-medium text-lg">Controle de acesso granular para administradores e operadores.</p>
        </div>
        <button 
          onClick={() => setIsCreateModalOpen(true)}
          className="bg-primary text-primary-foreground px-6 py-3 rounded-2xl font-bold flex items-center gap-2 hover:opacity-90 transition-all shadow-lg shadow-primary/20"
        >
          <UserPlus className="w-5 h-5" />
          Novo Administrador
        </button>
      </header>

      <CreateAdminModal 
        open={isCreateModalOpen} 
        onOpenChange={setIsCreateModalOpen} 
        roles={roles || []} 
      />

      <div className="flex gap-2 mb-8 bg-card p-1 rounded-2xl border border-border w-fit">
        {[
          { id: 'users', label: 'Usuários', icon: UserCheck },
          { id: 'roles', label: 'Cargos', icon: Shield },
          { id: 'audit', label: 'Auditoria', icon: History },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
              activeTab === tab.id ? 'bg-foreground text-background shadow-md' : 'hover:bg-muted text-muted-foreground'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-8">
        {activeTab === 'users' && (
          <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-muted/50 border-bottom border-border">
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Usuário</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Email</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Cargos</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Status</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {users?.map((user: any) => (
                  <tr key={user.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-bold text-foreground">{user.display_name || user.username}</div>
                      <div className="text-[10px] text-muted-foreground font-mono">{user.username}</div>
                    </td>
                    <td className="px-6 py-4 text-xs font-medium text-muted-foreground">{user.email || '-'}</td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {user.roles?.map((role: any) => (
                          <span key={role.id} className="px-2 py-0.5 bg-primary/10 text-primary text-[10px] font-black uppercase rounded">
                            {role.name}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {user.is_active ? (
                        <span className="flex items-center gap-1.5 text-emerald-600 text-[10px] font-black uppercase">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Ativo
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5 text-rose-600 text-[10px] font-black uppercase">
                          <ShieldAlert className="w-3.5 h-3.5" /> Inativo
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="text-xs font-bold text-primary hover:underline">Editar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'roles' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {roles?.map((role: any) => (
              <div key={role.id} className="bg-card border border-border rounded-3xl p-6 hover:border-primary/50 transition-all">
                <div className="flex justify-between items-start mb-4">
                  <div className="p-3 bg-primary/10 text-primary rounded-2xl">
                    <Shield className="w-6 h-6" />
                  </div>
                  {role.is_system && (
                    <span className="px-2 py-1 bg-muted rounded text-[10px] font-black uppercase tracking-tighter text-muted-foreground">
                      System
                    </span>
                  )}
                </div>
                <h3 className="text-xl font-black text-foreground mb-2">{role.name}</h3>
                <p className="text-sm text-muted-foreground mb-6 line-clamp-2">{role.description || 'Sem descrição.'}</p>
                <div className="border-t border-border pt-4">
                  <div className="text-[10px] font-black uppercase text-muted-foreground mb-2">Permissões ({role.permissions?.length || 0})</div>
                  <div className="flex flex-wrap gap-1">
                    {role.permissions?.slice(0, 5).map((p: any) => (
                      <span key={p.id} className="px-1.5 py-0.5 bg-muted rounded text-[8px] font-bold text-muted-foreground">
                        {p.code}
                      </span>
                    ))}
                    {(role.permissions?.length || 0) > 5 && (
                      <span className="px-1.5 py-0.5 bg-muted rounded text-[8px] font-bold text-muted-foreground">
                        +{(role.permissions?.length || 0) - 5}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <button className="border-2 border-dashed border-border rounded-3xl p-6 flex flex-col items-center justify-center gap-2 hover:bg-muted transition-all group">
              <Plus className="w-8 h-8 text-muted-foreground group-hover:text-primary transition-colors" />
              <span className="text-sm font-bold text-muted-foreground">Novo Cargo</span>
            </button>
          </div>
        )}

        {activeTab === 'audit' && (
          <div className="bg-foreground text-background rounded-3xl p-8 shadow-xl">
             <div className="space-y-6">
                {audit?.map((event: any) => (
                  <div key={event.id} className="flex items-start gap-4 border-l-2 border-primary/30 pl-6 py-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-xs font-black uppercase tracking-widest text-primary">{event.event_type}</span>
                        <span className={`text-[10px] font-black px-1.5 py-0.5 rounded ${event.status === 'success' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                          {event.status}
                        </span>
                      </div>
                      <div className="text-sm font-medium text-foreground-muted">
                        <span className="text-muted-foreground">Ator:</span> {event.actor_identifier}
                      </div>
                      <div className="text-[10px] font-mono text-muted-foreground mt-1">
                        {event.request_method} {event.request_path}
                      </div>
                    </div>
                    <div className="text-right">
                       <div className="text-[10px] font-bold text-muted-foreground">{new Date(event.created_at).toLocaleString('pt-BR')}</div>
                    </div>
                  </div>
                ))}
             </div>
          </div>
        )}
      </div>
    </div>
  )
}
