import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { Building2, LayoutGrid, ShieldCheck, Plus, Copy, RefreshCw, Power, Server, AlertCircle } from 'lucide-react'

type Organization = {
  id: string
  name: string
  slug: string
  status: string
  created_at: string
}

type Workspace = {
  id: string
  organization_id: string
  name: string
  slug: string
  created_at: string
}

type Appliance = {
  id: string
  workspace_id: string
  appliance_external_id: string
  name: string
  status: string
  version?: string | null
  health_status?: string | null
  readiness: boolean
  last_heartbeat_at?: string | null
  created_at: string
}

function StatCard({ label, value, hint, icon }: { label: string; value: string; hint: string; icon: ReactNode }) {
  return (
    <div className="rounded-3xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
          <p className="mt-2 text-3xl font-black text-foreground">{value}</p>
          <p className="mt-1 text-sm text-muted-foreground">{hint}</p>
        </div>
        <div className="rounded-2xl bg-primary/10 p-3 text-primary">{icon}</div>
      </div>
    </div>
  )
}

export default function ManagedControlPlane() {
  const queryClient = useQueryClient()
  const [orgName, setOrgName] = useState('')
  const [orgSlug, setOrgSlug] = useState('')
  const [workspaceName, setWorkspaceName] = useState('')
  const [workspaceSlug, setWorkspaceSlug] = useState('')
  const [workspaceOrgId, setWorkspaceOrgId] = useState('')
  const [tokenWorkspaceId, setTokenWorkspaceId] = useState('')
  const [enrollmentToken, setEnrollmentToken] = useState<string | null>(null)
  const [enrollmentExpiresAt, setEnrollmentExpiresAt] = useState<string | null>(null)

  const { data: organizations = [], isLoading: orgsLoading } = useQuery({
    queryKey: ['managed-organizations'],
    queryFn: async () => (await api.get('/managed/organizations')).data as Organization[],
  })

  const { data: workspaces = [], isLoading: workspacesLoading } = useQuery({
    queryKey: ['managed-workspaces'],
    queryFn: async () => (await api.get('/managed/workspaces')).data as Workspace[],
  })

  const { data: appliances = [], isLoading: appliancesLoading } = useQuery({
    queryKey: ['managed-appliances'],
    queryFn: async () => (await api.get('/managed/appliances')).data as Appliance[],
  })

  useEffect(() => {
    if (!workspaceOrgId && organizations.length > 0) {
      setWorkspaceOrgId(organizations[0].id)
    }
    if (!tokenWorkspaceId && workspaces.length > 0) {
      setTokenWorkspaceId(workspaces[0].id)
    }
  }, [organizations, workspaces, workspaceOrgId, tokenWorkspaceId])

  const createOrganization = useMutation({
    mutationFn: async () => {
      const res = await api.post('/managed/organizations', {
        name: orgName.trim(),
        slug: orgSlug.trim(),
      })
      return res.data as Organization
    },
    onSuccess: () => {
      setOrgName('')
      setOrgSlug('')
      queryClient.invalidateQueries({ queryKey: ['managed-organizations'] })
      queryClient.invalidateQueries({ queryKey: ['managed-workspaces'] })
    },
  })

  const createWorkspace = useMutation({
    mutationFn: async () => {
      const res = await api.post('/managed/workspaces', {
        organization_id: workspaceOrgId,
        name: workspaceName.trim(),
        slug: workspaceSlug.trim(),
      })
      return res.data as Workspace
    },
    onSuccess: () => {
      setWorkspaceName('')
      setWorkspaceSlug('')
      queryClient.invalidateQueries({ queryKey: ['managed-workspaces'] })
    },
  })

  const createEnrollmentToken = useMutation({
    mutationFn: async () => {
      const res = await api.post('/managed/appliances/enrollment-token', null, {
        params: {
          workspace_id: tokenWorkspaceId,
          expires_in_hours: 24,
        },
      })
      return res.data as { enrollment_token: string; expires_at: string }
    },
    onSuccess: data => {
      setEnrollmentToken(data.enrollment_token)
      setEnrollmentExpiresAt(data.expires_at)
    },
  })

  const revokeAppliance = useMutation({
    mutationFn: async (applianceId: string) => api.post(`/managed/appliances/${applianceId}/revoke`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['managed-appliances'] })
    },
  })

  const selectedWorkspaces = useMemo(
    () => workspaces.filter(workspace => !workspaceOrgId || workspace.organization_id === workspaceOrgId),
    [workspaces, workspaceOrgId],
  )

  const stats = useMemo(() => {
    const online = appliances.filter(appliance => appliance.status === 'online').length
    const revoked = appliances.filter(appliance => appliance.status === 'revoked').length
    return {
      orgs: organizations.length,
      workspaces: workspaces.length,
      appliances: appliances.length,
      online,
      revoked,
    }
  }, [organizations.length, workspaces.length, appliances])

  const isLoading = orgsLoading || workspacesLoading || appliancesLoading
  const formDisabled = !orgName.trim() || !orgSlug.trim() || createOrganization.isPending
  const workspaceDisabled = !workspaceOrgId || !workspaceName.trim() || !workspaceSlug.trim() || createWorkspace.isPending
  const tokenDisabled = !tokenWorkspaceId || createEnrollmentToken.isPending

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-8">
        <div className="inline-flex items-center gap-2 rounded-full border border-border bg-secondary px-3 py-1 text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground">
          <ShieldCheck className="h-3.5 w-3.5" />
          SaaS / Managed Control Plane
        </div>
        <h1 className="mt-4 text-4xl font-black tracking-tight text-foreground">
          Managed <span className="text-primary">Control Plane</span>
        </h1>
        <p className="mt-2 max-w-3xl text-muted-foreground">
          Esta tela agora reflete o backend real: organizações, workspaces, appliances e enrollment tokens.
          Não há, hoje, endpoints próprios para billing/support/link sync neste módulo.
        </p>
      </header>

      <div className="mb-8 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Organizations" value={String(stats.orgs)} hint="Registradas no backend" icon={<Building2 className="h-5 w-5" />} />
        <StatCard label="Workspaces" value={String(stats.workspaces)} hint="Vinculados a organizações" icon={<LayoutGrid className="h-5 w-5" />} />
        <StatCard label="Appliances" value={String(stats.appliances)} hint="Enrolled ou ativos" icon={<Server className="h-5 w-5" />} />
        <StatCard label="Online" value={String(stats.online)} hint="Com heartbeat recente" icon={<RefreshCw className="h-5 w-5" />} />
        <StatCard label="Revoked" value={String(stats.revoked)} hint="Bloqueados no backend" icon={<Power className="h-5 w-5" />} />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <section className="rounded-3xl border border-border bg-card p-6 shadow-sm xl:col-span-1">
          <div className="mb-5 flex items-center gap-2">
            <Plus className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-black text-foreground">Criar Organização</h2>
          </div>
          <div className="space-y-3">
            <input
              value={orgName}
              onChange={e => setOrgName(e.target.value)}
              placeholder="Nome da organização"
              className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
            />
            <input
              value={orgSlug}
              onChange={e => setOrgSlug(e.target.value)}
              placeholder="slug"
              className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
            />
            <button
              onClick={() => createOrganization.mutate()}
              disabled={formDisabled}
              className="w-full rounded-2xl bg-foreground px-4 py-3 text-sm font-bold text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {createOrganization.isPending ? 'Criando...' : 'Criar Organização'}
            </button>
          </div>

          <div className="mt-8 border-t border-border pt-6">
            <h3 className="mb-3 text-sm font-black uppercase tracking-[0.2em] text-muted-foreground">Organizações</h3>
            <div className="space-y-2">
              {isLoading && <div className="text-sm text-muted-foreground">Carregando...</div>}
              {!isLoading && organizations.length === 0 && (
                <div className="rounded-2xl border border-dashed border-border bg-secondary/50 p-4 text-sm text-muted-foreground">
                  Nenhuma organização cadastrada.
                </div>
              )}
              {organizations.map(org => (
                <div key={org.id} className="rounded-2xl border border-border bg-secondary/40 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-bold text-foreground">{org.name}</div>
                      <div className="text-xs text-muted-foreground">{org.slug}</div>
                    </div>
                    <span className="rounded-full bg-primary/10 px-2 py-1 text-[10px] font-black uppercase tracking-[0.2em] text-primary">
                      {org.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-3xl border border-border bg-card p-6 shadow-sm xl:col-span-1">
          <div className="mb-5 flex items-center gap-2">
            <Plus className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-black text-foreground">Criar Workspace</h2>
          </div>
          <div className="space-y-3">
            <select
              value={workspaceOrgId}
              onChange={e => setWorkspaceOrgId(e.target.value)}
              className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
            >
              <option value="">Selecione a organização</option>
              {organizations.map(org => (
                <option key={org.id} value={org.id}>
                  {org.name}
                </option>
              ))}
            </select>
            <input
              value={workspaceName}
              onChange={e => setWorkspaceName(e.target.value)}
              placeholder="Nome do workspace"
              className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
            />
            <input
              value={workspaceSlug}
              onChange={e => setWorkspaceSlug(e.target.value)}
              placeholder="slug"
              className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
            />
            <button
              onClick={() => createWorkspace.mutate()}
              disabled={workspaceDisabled}
              className="w-full rounded-2xl bg-foreground px-4 py-3 text-sm font-bold text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {createWorkspace.isPending ? 'Criando...' : 'Criar Workspace'}
            </button>
          </div>

          <div className="mt-8 border-t border-border pt-6">
            <h3 className="mb-3 text-sm font-black uppercase tracking-[0.2em] text-muted-foreground">Workspaces</h3>
            <div className="space-y-2">
              {workspaces.length === 0 && !isLoading && (
                <div className="rounded-2xl border border-dashed border-border bg-secondary/50 p-4 text-sm text-muted-foreground">
                  Nenhum workspace cadastrado.
                </div>
              )}
              {selectedWorkspaces.map(workspace => {
                const org = organizations.find(item => item.id === workspace.organization_id)
                return (
                  <div key={workspace.id} className="rounded-2xl border border-border bg-secondary/40 p-4">
                    <div className="font-bold text-foreground">{workspace.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {workspace.slug} · {org?.name || workspace.organization_id}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        <section className="rounded-3xl border border-border bg-card p-6 shadow-sm xl:col-span-1">
          <div className="mb-5 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-black text-foreground">Appliances</h2>
          </div>

          <div className="space-y-3">
            <select
              value={tokenWorkspaceId}
              onChange={e => setTokenWorkspaceId(e.target.value)}
              className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
            >
              <option value="">Selecione o workspace</option>
              {workspaces.map(workspace => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => createEnrollmentToken.mutate()}
              disabled={tokenDisabled}
              className="w-full rounded-2xl bg-primary px-4 py-3 text-sm font-bold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {createEnrollmentToken.isPending ? 'Gerando...' : 'Gerar Enrollment Token'}
            </button>
            {enrollmentToken && (
              <div className="rounded-2xl border border-border bg-secondary/50 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground">Token</p>
                    <p className="mt-1 break-all font-mono text-xs text-foreground">{enrollmentToken}</p>
                    {enrollmentExpiresAt && <p className="mt-2 text-xs text-muted-foreground">Expira em {new Date(enrollmentExpiresAt).toLocaleString()}</p>}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => createEnrollmentToken.mutate()}
                      className="rounded-xl border border-border bg-background px-3 py-2 text-xs font-bold text-muted-foreground transition-colors hover:text-foreground hover:bg-secondary"
                      title="Rotacionar token"
                      disabled={createEnrollmentToken.isPending || !tokenWorkspaceId}
                    >
                      {createEnrollmentToken.isPending ? 'Rotacionando...' : 'Rotacionar'}
                    </button>
                    <button
                      onClick={() => navigator.clipboard.writeText(enrollmentToken)}
                      className="rounded-xl border border-border bg-background p-2 text-muted-foreground transition-colors hover:text-foreground"
                      title="Copiar token"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="mt-8 border-t border-border pt-6">
            <h3 className="mb-3 text-sm font-black uppercase tracking-[0.2em] text-muted-foreground">Appliances registrados</h3>
            <div className="space-y-3">
              {appliances.length === 0 && !isLoading && (
                <div className="rounded-2xl border border-dashed border-border bg-secondary/50 p-4 text-sm text-muted-foreground">
                  Nenhum appliance enrolled.
                </div>
              )}
              {appliances.map(appliance => {
                const workspace = workspaces.find(item => item.id === appliance.workspace_id)
                const healthLabel = appliance.health_status || 'unknown'
                return (
                  <div key={appliance.id} className="rounded-2xl border border-border bg-secondary/40 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="font-bold text-foreground">{appliance.name}</div>
                        <div className="text-xs text-muted-foreground">{workspace?.name || appliance.workspace_id}</div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {appliance.version || 'sem versão'} · {appliance.readiness ? 'ready' : 'not ready'}
                        </div>
                      </div>
                      <span className="rounded-full bg-primary/10 px-2 py-1 text-[10px] font-black uppercase tracking-[0.2em] text-primary">
                        {healthLabel}
                      </span>
                    </div>
                    <div className="mt-4 flex items-center justify-between gap-3">
                      <span className="text-xs font-medium text-muted-foreground">{appliance.status}</span>
                      <button
                        onClick={() => revokeAppliance.mutate(appliance.id)}
                        className="inline-flex items-center gap-2 rounded-xl bg-destructive px-3 py-2 text-xs font-bold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                        disabled={revokeAppliance.isPending}
                      >
                        <Power className="h-3.5 w-3.5" />
                        Revoke
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
