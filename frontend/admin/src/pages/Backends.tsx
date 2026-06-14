import { useMemo, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Cpu,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Server,
  Square,
  Terminal,
} from 'lucide-react'
import { toast } from 'sonner'
import type { ColumnDef } from '@tanstack/react-table'

import { AdvancedTable } from '../components/table/advanced-table'
import api from '../lib/api'

type Backend = {
  id: string
  name: string
  provider: string
  backend_url: string
  healthcheck_path: string
  is_active: boolean
  is_default: boolean
  status: string
  max_parallel_requests: number
  current_running: number
  metadata_json?: string | null
  health?: {
    ok?: boolean
    status?: string
    detail?: string
  } | null
}

type BackendForm = {
  name: string
  provider: string
  backend_url: string
  healthcheck_path: string
  is_active: boolean
  is_default: boolean
  status: string
  max_parallel_requests: number
  metadata_json: string
}

const EMPTY_FORM: BackendForm = {
  name: '',
  provider: 'llama.cpp',
  backend_url: '',
  healthcheck_path: '/health',
  is_active: true,
  is_default: false,
  status: 'configured',
  max_parallel_requests: 8,
  metadata_json: '',
}

export default function Backends() {
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 10 })
  const [filters, setFilters] = useState<any>({})
  const [sorting, setSorting] = useState<any[]>([])
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [selectedBackend, setSelectedBackend] = useState<Backend | null>(null)
  const [backendForm, setBackendForm] = useState<BackendForm>(EMPTY_FORM)
  const [testedModels, setTestedModels] = useState<any[] | null>(null)

  const { data: backendsData, isLoading } = useQuery<{ items: Backend[]; total: number }>({
    queryKey: ['backends', pagination, filters, sorting],
    queryFn: async () => {
      const res = await api.get('/admin/backends', {
        params: {
          page: pagination.pageIndex + 1,
          limit: pagination.pageSize,
          ...filters,
        },
      })
      const payload = res.data
      if (Array.isArray(payload)) return { items: payload, total: payload.length }
      return {
        items: Array.isArray(payload?.items) ? payload.items : [],
        total: typeof payload?.total === 'number' ? payload.total : 0,
      }
    },
  })

  const backends = backendsData?.items || []
  const selected = selectedBackend || backends[0] || null

  const { data: selectedHealth } = useQuery({
    queryKey: ['backend-health', selected?.id],
    queryFn: async () => {
      if (!selected?.id) return null
      return api.getBackendHealth(selected.id)
    },
    enabled: !!selected?.id,
  })

  const { data: selectedLogs } = useQuery({
    queryKey: ['backend-logs', selected?.id],
    queryFn: async () => {
      if (!selected?.id) return null
      return api.getBackendLogs(selected.id)
    },
    enabled: !!selected?.id,
  })

  const actionMutation = useMutation({
    mutationFn: async ({ id, action }: { id: string; action: 'start' | 'stop' | 'restart' | 'reconcile' }) => {
      if (action === 'start') return api.startBackend(id)
      if (action === 'stop') return api.stopBackend(id)
      if (action === 'restart') return api.restartBackend(id)
      return api.reconcileBackend(id)
    },
    onSuccess: (_, variables) => {
      toast.success(`Ação ${variables.action} executada.`)
      queryClient.invalidateQueries({ queryKey: ['backends'] })
      queryClient.invalidateQueries({ queryKey: ['backend-health', variables.id] })
      queryClient.invalidateQueries({ queryKey: ['backend-logs', variables.id] })
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Falha na operação do backend')
    },
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: backendForm.name.trim(),
        provider: backendForm.provider,
        backend_url: backendForm.backend_url.trim(),
        healthcheck_path: backendForm.healthcheck_path.trim() || '/health',
        is_active: backendForm.is_active,
        is_default: backendForm.is_default,
        status: backendForm.status.trim() || 'configured',
        max_parallel_requests: Number(backendForm.max_parallel_requests) || 8,
        metadata_json: backendForm.metadata_json.trim() || null,
      }
      return api.createBackend(payload)
    },
    onSuccess: () => {
      toast.success('Backend criado com sucesso.')
      setIsCreateOpen(false)
      setBackendForm(EMPTY_FORM)
      queryClient.invalidateQueries({ queryKey: ['backends'] })
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Falha ao criar backend')
    },
  })

  const testConnectionMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: backendForm.name.trim() || 'preview-backend',
        provider: backendForm.provider,
        backend_url: backendForm.backend_url.trim(),
        healthcheck_path: backendForm.healthcheck_path.trim() || '/health',
        is_active: backendForm.is_active,
        is_default: backendForm.is_default,
        status: backendForm.status.trim() || 'configured',
        max_parallel_requests: Number(backendForm.max_parallel_requests) || 8,
        metadata_json: backendForm.metadata_json.trim() || null,
      }
      return api.testConnection(payload)
    },
    onSuccess: (result: any) => {
      toast.success(result?.ok ? 'Conexao validada com sucesso.' : 'Backend respondeu sem health OK.')
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Falha ao testar conexao')
    },
  })

  const listModelsMutation = useMutation({
    mutationFn: async () => {
      if (!selected) throw new Error('Selecione um backend primeiro.')
      return api.listBackendModels({
        name: selected.name,
        provider: selected.provider,
        backend_url: selected.backend_url,
        healthcheck_path: selected.healthcheck_path,
        is_active: selected.is_active,
        is_default: selected.is_default,
        status: selected.status,
        max_parallel_requests: selected.max_parallel_requests,
        metadata_json: selected.metadata_json || null,
      })
    },
    onSuccess: (result: any) => {
      setTestedModels(Array.isArray(result) ? result : result?.data || result?.models || [])
      toast.success('Modelos remotos carregados.')
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Falha ao listar modelos do backend')
    },
  })

  const activeCount = backends.filter(item => item.is_active).length
  const providersCount = new Set(backends.map(item => item.provider)).size
  const totalRunning = backends.reduce((acc, item) => acc + (item.current_running || 0), 0)

  const columns = useMemo<ColumnDef<Backend>[]>(() => [
    {
      accessorKey: 'name',
      header: 'Backend',
      cell: ({ row }) => (
        <button
          type="button"
          onClick={() => setSelectedBackend(row.original)}
          className="flex w-full items-center gap-3 text-left"
        >
          <div className={`rounded-lg p-2 ${row.original.is_active ? 'bg-primary/10 text-primary' : 'bg-secondary text-muted-foreground'}`}>
            <Cpu className="h-4 w-4" />
          </div>
          <div>
            <div className="font-bold text-foreground">{row.original.name}</div>
            <div className="text-[10px] font-mono text-muted-foreground">{row.original.id}</div>
          </div>
        </button>
      ),
    },
    {
      accessorKey: 'backend_url',
      header: 'Endpoint',
      cell: ({ row }) => (
        <div className="max-w-[260px] truncate text-[10px] font-mono text-muted-foreground">
          {row.original.backend_url}
        </div>
      ),
    },
    {
      accessorKey: 'provider',
      header: 'Provider',
      cell: ({ row }) => (
        <span className="rounded-md bg-secondary px-2 py-0.5 text-[10px] font-black uppercase text-muted-foreground">
          {row.original.provider}
        </span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Estado',
      cell: ({ row }) => {
        const ok = row.original.health?.ok ?? row.original.is_active
        return ok ? (
          <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase text-emerald-600">
            <CheckCircle2 className="h-3.5 w-3.5" /> {row.original.status || 'healthy'}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase text-destructive">
            <AlertCircle className="h-3.5 w-3.5" /> {row.original.status || 'offline'}
          </span>
        )
      },
    },
    {
      accessorKey: 'max_parallel_requests',
      header: 'Capacidade',
      cell: ({ row }) => (
        <div className="text-xs text-foreground">
          <div>{row.original.current_running || 0} em execucao</div>
          <div className="text-[10px] text-muted-foreground">max {row.original.max_parallel_requests || 0}</div>
        </div>
      ),
    },
    {
      id: 'actions',
      header: 'Acoes',
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={() => actionMutation.mutate({ id: row.original.id, action: row.original.is_active ? 'stop' : 'start' })}
            className="rounded-lg p-2 text-muted-foreground transition-all hover:bg-secondary"
          >
            {row.original.is_active ? <Square className="h-4 w-4" /> : <Play className="h-4 w-4 text-primary" />}
          </button>
          <button
            type="button"
            onClick={() => actionMutation.mutate({ id: row.original.id, action: 'restart' })}
            className="rounded-lg p-2 text-muted-foreground transition-all hover:bg-secondary"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>
      ),
      enableHiding: false,
    },
  ], [actionMutation])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">Backends</h1>
          <p className="text-sm md:text-lg text-muted-foreground">Controle operacional de providers, health, logs e lifecycle.</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['backends'] })}
            className="rounded-xl border border-border px-4 py-2.5 text-sm font-bold text-foreground hover:bg-secondary"
          >
            Atualizar
          </button>
          <button
            type="button"
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white shadow-lg shadow-primary/20 hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            Novo Backend
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Total" value={String(backends.length)} icon={<Server className="h-5 w-5" />} />
        <MetricCard label="Ativos" value={String(activeCount)} icon={<CheckCircle2 className="h-5 w-5 text-emerald-500" />} />
        <MetricCard label="Providers" value={String(providersCount)} icon={<Cpu className="h-5 w-5" />} />
        <MetricCard label="Execucoes" value={String(totalRunning)} icon={<Activity className="h-5 w-5 text-primary" />} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.35fr,0.65fr]">
        <AdvancedTable
          id="backends"
          columns={columns}
          data={backends}
          rowCount={backendsData?.total || backends.length}
          isLoading={isLoading}
          pagination={pagination}
          onPaginationChange={setPagination}
          onSortingChange={setSorting}
          onFiltersApply={setFilters}
          filterConfig={[
            { id: 'name', label: 'Nome', type: 'text' },
            { id: 'provider', label: 'Provider', type: 'text' },
          ]}
        />

        <div className="space-y-4 rounded-3xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-black text-foreground">{selected?.name || 'Nenhum backend'}</h2>
              <p className="text-xs text-muted-foreground">{selected?.backend_url || 'Selecione um backend para ver detalhes.'}</p>
            </div>
            {selected && (
              <button
                type="button"
                onClick={() => actionMutation.mutate({ id: selected.id, action: 'reconcile' })}
                className="rounded-xl border border-border px-3 py-2 text-xs font-bold hover:bg-secondary"
              >
                Reconcile
              </button>
            )}
          </div>

          {selected ? (
            <>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <DetailCard label="Provider" value={selected.provider} />
                <DetailCard label="Status" value={selected.status} />
                <DetailCard label="Health path" value={selected.healthcheck_path} mono />
                <DetailCard label="Concurrency" value={`${selected.current_running || 0}/${selected.max_parallel_requests || 0}`} />
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => listModelsMutation.mutate()}
                  className="rounded-xl bg-secondary px-3 py-2 text-xs font-bold text-foreground hover:bg-secondary/80"
                >
                  Listar Modelos
                </button>
                <button
                  type="button"
                  onClick={() => queryClient.invalidateQueries({ queryKey: ['backend-health', selected.id] })}
                  className="rounded-xl bg-secondary px-3 py-2 text-xs font-bold text-foreground hover:bg-secondary/80"
                >
                  Health
                </button>
              </div>

              <section className="space-y-2">
                <div className="text-xs font-black uppercase tracking-widest text-muted-foreground">Health detalhado</div>
                <pre className="overflow-x-auto rounded-2xl bg-background p-3 text-[10px] text-foreground">
                  {JSON.stringify(selectedHealth || selected.health || {}, null, 2)}
                </pre>
              </section>

              <section className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-muted-foreground">
                  <Terminal className="h-3.5 w-3.5" />
                  Logs
                </div>
                <pre className="max-h-56 overflow-auto rounded-2xl bg-background p-3 text-[10px] text-foreground">
                  {typeof selectedLogs === 'string'
                    ? selectedLogs
                    : JSON.stringify(selectedLogs || {}, null, 2)}
                </pre>
              </section>

              {testedModels && (
                <section className="space-y-2">
                  <div className="text-xs font-black uppercase tracking-widest text-muted-foreground">Modelos remotos</div>
                  <div className="rounded-2xl bg-background p-3 text-xs text-foreground">
                    {testedModels.length ? testedModels.map((item, index) => (
                      <div key={index} className="py-1 font-mono">
                        {typeof item === 'string' ? item : JSON.stringify(item)}
                      </div>
                    )) : 'Nenhum modelo retornado.'}
                  </div>
                </section>
              )}
            </>
          ) : (
            <div className="rounded-2xl border border-dashed border-border p-6 text-sm text-muted-foreground">
              Nenhum backend encontrado.
            </div>
          )}
        </div>
      </div>

      {isCreateOpen && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-foreground/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-3xl rounded-3xl border border-border bg-card shadow-2xl">
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <div>
                <h2 className="text-xl font-black text-foreground">Novo Backend</h2>
                <p className="text-sm text-muted-foreground">Cadastro real contra `POST /admin/backends`.</p>
              </div>
              <button
                type="button"
                onClick={() => setIsCreateOpen(false)}
                className="rounded-xl border border-border px-3 py-2 text-sm font-bold hover:bg-secondary"
              >
                Fechar
              </button>
            </div>

            <div className="grid gap-4 p-6 md:grid-cols-2">
              <FormField label="Nome">
                <input value={backendForm.name} onChange={e => setBackendForm(prev => ({ ...prev, name: e.target.value }))} className={inputClassName} />
              </FormField>
              <FormField label="Provider">
                <select value={backendForm.provider} onChange={e => setBackendForm(prev => ({ ...prev, provider: e.target.value }))} className={inputClassName}>
                  <option value="llama.cpp">llama.cpp</option>
                  <option value="vllm">vllm</option>
                  <option value="openai_compatible">openai_compatible</option>
                  <option value="ollama">ollama</option>
                  <option value="openai">openai</option>
                  <option value="anthropic">anthropic</option>
                </select>
              </FormField>
              <FormField label="Backend URL">
                <input value={backendForm.backend_url} onChange={e => setBackendForm(prev => ({ ...prev, backend_url: e.target.value }))} className={inputClassName} placeholder="http://localhost:8001" />
              </FormField>
              <FormField label="Healthcheck">
                <input value={backendForm.healthcheck_path} onChange={e => setBackendForm(prev => ({ ...prev, healthcheck_path: e.target.value }))} className={inputClassName} />
              </FormField>
              <FormField label="Status">
                <input value={backendForm.status} onChange={e => setBackendForm(prev => ({ ...prev, status: e.target.value }))} className={inputClassName} />
              </FormField>
              <FormField label="Max Parallel Requests">
                <input type="number" value={backendForm.max_parallel_requests} onChange={e => setBackendForm(prev => ({ ...prev, max_parallel_requests: Number(e.target.value) }))} className={inputClassName} />
              </FormField>
              <label className="flex items-center gap-3 rounded-2xl border border-border bg-secondary/40 px-4 py-3">
                <input type="checkbox" checked={backendForm.is_active} onChange={e => setBackendForm(prev => ({ ...prev, is_active: e.target.checked }))} />
                <span className="text-sm font-medium text-foreground">Ativo</span>
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-border bg-secondary/40 px-4 py-3">
                <input type="checkbox" checked={backendForm.is_default} onChange={e => setBackendForm(prev => ({ ...prev, is_default: e.target.checked }))} />
                <span className="text-sm font-medium text-foreground">Default</span>
              </label>
              <FormField label="Metadata JSON">
                <textarea value={backendForm.metadata_json} onChange={e => setBackendForm(prev => ({ ...prev, metadata_json: e.target.value }))} className={`${inputClassName} min-h-[120px]`} />
              </FormField>
            </div>

            <div className="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
              <button type="button" onClick={() => testConnectionMutation.mutate()} className="rounded-2xl border border-border px-4 py-2.5 text-sm font-bold hover:bg-secondary">
                {testConnectionMutation.isPending ? 'Testando...' : 'Testar conexao'}
              </button>
              <button type="button" onClick={() => createMutation.mutate()} disabled={createMutation.isPending || !backendForm.name.trim() || !backendForm.backend_url.trim()} className="rounded-2xl bg-primary px-5 py-2.5 text-sm font-bold text-white hover:bg-primary/90 disabled:opacity-50">
                {createMutation.isPending ? 'Criando...' : 'Criar backend'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, icon }: { label: string; value: string; icon: ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="mb-2 flex items-center gap-3 text-muted-foreground">{icon}</div>
      <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="text-2xl font-black text-foreground">{value}</div>
    </div>
  )
}

function DetailCard({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-2xl border border-border bg-background p-3">
      <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className={`mt-1 text-sm text-foreground ${mono ? 'font-mono text-xs' : 'font-semibold'}`}>{value}</div>
    </div>
  )
}

function FormField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="space-y-2 md:col-span-1">
      <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">{label}</span>
      {children}
    </label>
  )
}

const inputClassName = 'w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary'
