import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArchiveRestore, CheckCircle2, FileKey2, RefreshCw, ShieldAlert, Check, X, Clock, AlertTriangle, AlertCircle } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import api from '../../lib/api'

type BackupRow = {
  id: string
  created_at: string
  component_count: number
  status: string
  archive_checksum: string
  backup_type?: string
}

export default function BackupDashboard() {
  const queryClient = useQueryClient()
  const [selectedBackupId, setSelectedBackupId] = useState<string | null>(null)

  const { data: backups, isLoading } = useQuery<BackupRow[]>({
    queryKey: ['backups'],
    queryFn: async () => api.listBackups(),
    refetchInterval: 15000,
  })

  const selected = backups?.find(item => item.id === selectedBackupId) || backups?.[0] || null

  const { data: selectedDetails } = useQuery({
    queryKey: ['backupDetails', selected?.id],
    queryFn: async () => {
      if (!selected?.id) return null
      return api.getBackup(selected.id)
    },
    enabled: !!selected?.id,
  })

  const { data: auditEvents } = useQuery<any[]>({
    queryKey: ['rbacAudit'],
    queryFn: async () => api.listRbacAudit(100),
    refetchInterval: 15000,
  })

  const createBackup = useMutation({
    mutationFn: async () => api.createLogicalAgentBackup(),
    onSuccess: () => {
      toast.success('Backup de agentes (lógico) criado e verificado automaticamente.')
      queryClient.invalidateQueries({ queryKey: ['backups'] })
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Falha ao criar backup.')
    },
  })

  const verifyBackup = useMutation({
    mutationFn: async (id: string) => api.verifyBackup(id),
    onSuccess: (result) => {
      toast.success(`Verificação concluída: ${result.status}`)
      queryClient.invalidateQueries({ queryKey: ['backups'] })
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Falha ao verificar backup.')
    },
  })

  const restoreBackup = useMutation({
    mutationFn: async ({ id, dryRun }: { id: string; dryRun: boolean }) => api.restoreBackup(id, dryRun),
    onSuccess: (result) => {
      toast.success(result.status === 'dry_run_complete' ? 'Dry-run concluído.' : 'Restore concluído.')
      queryClient.invalidateQueries({ queryKey: ['backups'] })
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Falha ao restaurar backup.')
    },
  })

  const [activeRequest, setActiveRequest] = useState<any | null>(null)
  const [execToken, setExecToken] = useState<string>('')

  const createRestoreRequest = useMutation({
    mutationFn: async ({ backupId, dryRun }: { backupId: string; dryRun: boolean }) =>
      api.createRestoreRequest(backupId, dryRun),
    onSuccess: (data) => {
      toast.success('Solicitação de restore criada com sucesso. Aguardando aprovação.')
      setActiveRequest(data)
      queryClient.invalidateQueries({ queryKey: ['backups'] })
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Falha ao criar solicitação de restore.')
    },
  })

  const approveRestoreRequest = useMutation({
    mutationFn: async (id: string) => api.approveRestoreRequest(id),
    onSuccess: (data) => {
      toast.success('Solicitação de restore aprovada!')
      setActiveRequest(data)
      if (data.token) {
        setExecToken(data.token)
      }
      queryClient.invalidateQueries({ queryKey: ['backups'] })
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Falha ao aprovar restore.')
    },
  })

  const executeRestoreRequest = useMutation({
    mutationFn: async ({ id, token }: { id: string; token: string }) =>
      api.executeRestoreRequest(id, token),
    onSuccess: (result) => {
      toast.success(result.status === 'dry_run_complete' ? 'Dry-run concluído.' : 'Restore produtivo concluído com sucesso!')
      if (activeRequest) {
        setActiveRequest({ ...activeRequest, status: 'executed' })
      }
      queryClient.invalidateQueries({ queryKey: ['backups'] })
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Falha ao executar restore.')
    },
  })

  const restoreResult = restoreBackup.data || executeRestoreRequest.data

  // 1. Last successful backup
  const lastSuccessBackup = backups?.find(b => b.status === 'valid')

  // 2. Backup Age calculation
  let backupAgeStr = 'n/a'
  if (lastSuccessBackup) {
    const diffMs = Date.now() - new Date(lastSuccessBackup.created_at).getTime()
    const diffSecs = Math.max(0, Math.floor(diffMs / 1000))
    if (diffSecs < 60) {
      backupAgeStr = `${diffSecs}s`
    } else if (diffSecs < 3600) {
      backupAgeStr = `${Math.floor(diffSecs / 60)}m`
    } else if (diffSecs < 86400) {
      backupAgeStr = `${Math.floor(diffSecs / 3600)}h`
    } else {
      backupAgeStr = `${Math.floor(diffSecs / 86400)}d`
    }
  }

  // 3. Components included/excluded from manifest
  const includedComponents = selectedDetails?.included || ['agents', 'workflows', 'embedding metadata']
  const excludedComponents = selectedDetails?.excluded || ['auth', 'tenants', 'billing', 'audit', 'policies', 'persisted config']

  // 4. Last restore validation
  const lastRestoreValidation = selectedDetails?.last_verified_at 
    ? new Date(selectedDetails.last_verified_at).toLocaleString() 
    : (selected?.status === 'valid' ? 'Validado na criação' : 'Pendente')

  // 5. Recent failures (from backups list and RBAC audit logs)
  const recentFailures = [
    ...(backups?.filter(b => b.status === 'corrupted' || b.status === 'failed').map(b => ({
      id: b.id,
      type: 'Backup Corrompido',
      target: b.id,
      timestamp: b.created_at,
      error: 'Falha na verificação de assinatura/checksum'
    })) || []),
    ...(auditEvents?.filter(e => e.status === 'failed' && (e.event_type || '').startsWith('backup')).map(e => ({
      id: e.id || String(Math.random()),
      type: 'Falha/Rollback',
      target: e.target_id || 'n/a',
      timestamp: e.created_at || new Date().toISOString(),
      error: e.metadata?.promotion_error || e.metadata?.reason || 'Falha na operação'
    })) || [])
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-black uppercase tracking-[0.2em] text-muted-foreground">
            <FileKey2 className="h-4 w-4" />
            Disaster Recovery
          </div>
          <h1 className="mt-4 text-4xl font-black tracking-tight text-foreground">Backup Dashboard</h1>
          <p className="mt-2 max-w-2xl text-sm font-medium text-muted-foreground">
            Backups lógicos de agentes com criptografia, assinatura, checksum e verificação automática antes do restore.
          </p>
        </div>
        <button
          type="button"
          onClick={() => createBackup.mutate()}
          disabled={createBackup.isPending}
          className="inline-flex items-center justify-center gap-2 rounded-2xl bg-foreground px-5 py-3 text-sm font-black text-background transition-opacity hover:opacity-90 disabled:opacity-50 cursor-pointer"
        >
          {createBackup.isPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <ArchiveRestore className="h-4 w-4" />}
          Criar `llmstack backup --logical-agent-backup`
        </button>
      </header>

      {/* Operational Metrics Cards */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="Backups disponíveis" value={String(backups?.length || 0)} tone="neutral" />
        <MetricCard title="Último Backup" value={lastSuccessBackup ? lastSuccessBackup.id.slice(7, 21) : 'n/a'} tone="good" subtitle="Último bem-sucedido" />
        <MetricCard title="Idade do Backup" value={backupAgeStr} tone={backupAgeStr === 'n/a' ? 'neutral' : 'warn'} subtitle="Tempo desde o último backup" />
        <MetricCard title="Última Validação" value={selected?.status || 'n/a'} tone={selected?.status === 'valid' ? 'good' : 'warn'} subtitle={lastRestoreValidation} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
        <div className="space-y-6">
          {/* History Section */}
          <section className="rounded-3xl border border-border bg-card shadow-sm overflow-hidden">
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <div>
                <h2 className="text-lg font-black text-foreground">Histórico de Backups</h2>
                <p className="text-sm text-muted-foreground">Cada pacote já sai validado logo após a criação.</p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-border text-sm">
                <thead className="bg-secondary/50 text-left text-xs font-black uppercase tracking-[0.16em] text-muted-foreground">
                  <tr>
                    <th className="px-6 py-3">Backup</th>
                    <th className="px-6 py-3">Criado em</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3">Checksum</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {isLoading ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-8 text-center text-muted-foreground">Carregando backups...</td>
                    </tr>
                  ) : backups?.length ? (
                    backups.map(backup => (
                      <tr
                        key={backup.id}
                        onClick={() => setSelectedBackupId(backup.id)}
                        className={`cursor-pointer transition-colors hover:bg-secondary/40 ${selected?.id === backup.id ? 'bg-secondary/60' : ''}`}
                      >
                        <td className="px-6 py-4 font-semibold text-foreground">
                          <div className="flex flex-col gap-1">
                            <span>{backup.id}</span>
                            {backup.backup_type === 'pre-restore-safety-backup' && (
                              <span className="inline-flex w-fit items-center gap-1 rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-700 border border-amber-200">
                                Segurança pré-restore
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-muted-foreground">{new Date(backup.created_at).toLocaleString()}</td>
                        <td className="px-6 py-4">
                          <StatusPill status={backup.status} />
                        </td>
                        <td className="px-6 py-4 font-mono text-xs text-muted-foreground">{backup.archive_checksum.slice(0, 16)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="px-6 py-8 text-center text-muted-foreground">Nenhum backup criado ainda.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* Included / Excluded Components Section */}
          <section className="rounded-3xl border border-border bg-card p-6 shadow-sm">
            <h2 className="text-lg font-black text-foreground mb-4">Componentes no Backup Selecionado</h2>
            {selected ? (
              <div className="grid gap-6 sm:grid-cols-2">
                <div className="space-y-3">
                  <h3 className="text-sm font-black uppercase tracking-wider text-emerald-600 flex items-center gap-1.5">
                    <Check className="h-4 w-4 stroke-[3px]" /> Componentes Incluídos
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {includedComponents.map((comp: string) => (
                      <span key={comp} className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 border border-emerald-100">
                        {comp}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="space-y-3">
                  <h3 className="text-sm font-black uppercase tracking-wider text-rose-500 flex items-center gap-1.5">
                    <X className="h-4 w-4 stroke-[3px]" /> Componentes Excluídos
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {excludedComponents.map((comp: string) => (
                      <span key={comp} className="inline-flex items-center gap-1.5 rounded-xl bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 border border-rose-100">
                        {comp}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Selecione um backup para ver a lista de componentes.</p>
            )}
          </section>
        </div>

        <div className="space-y-6">
          {/* Action / Recovery Section */}
          <section className="rounded-3xl border border-border bg-card p-6 shadow-sm">
            <h2 className="text-lg font-black text-foreground">Recuperação</h2>
            {selected ? (
              <>
                <div className="mt-4 rounded-2xl border border-border bg-secondary/50 p-4">
                  <p className="text-xs font-black uppercase tracking-[0.16em] text-muted-foreground">Backup selecionado</p>
                  <p className="mt-2 text-base font-bold text-foreground">{selected.id}</p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {selected.component_count} componentes, checksum {selected.archive_checksum.slice(0, 20)}...
                  </p>
                </div>

                <div className="mt-6 space-y-3">
                  <button
                    type="button"
                    onClick={() => verifyBackup.mutate(selected.id)}
                    disabled={verifyBackup.isPending}
                    className="flex w-full items-center justify-center gap-2 rounded-2xl border border-border bg-background px-4 py-3 font-bold text-foreground transition-colors hover:bg-secondary disabled:opacity-50 cursor-pointer"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    Verificar integridade
                  </button>
                  <button
                    type="button"
                    onClick={() => restoreBackup.mutate({ id: selected.id, dryRun: true })}
                    disabled={restoreBackup.isPending}
                    className="flex w-full items-center justify-center gap-2 rounded-2xl border border-border bg-background px-4 py-3 font-bold text-foreground transition-colors hover:bg-secondary disabled:opacity-50 cursor-pointer"
                  >
                    <ShieldAlert className="h-4 w-4" />
                    Simular restore (Staging)
                  </button>

                  <div className="border-t border-border my-4 pt-4">
                    <h3 className="text-sm font-black uppercase tracking-wider text-foreground mb-3">Restore Produtivo (Aprovação Forte)</h3>
                    
                    {!activeRequest ? (
                      <button
                        type="button"
                        onClick={() => createRestoreRequest.mutate({ backupId: selected.id, dryRun: false })}
                        disabled={createRestoreRequest.isPending}
                        className="flex w-full items-center justify-center gap-2 rounded-2xl bg-amber-600 px-4 py-3 font-black text-white transition-opacity hover:opacity-90 disabled:opacity-50 cursor-pointer"
                      >
                        <ArchiveRestore className="h-4 w-4" />
                        Solicitar Restore Produtivo
                      </button>
                    ) : (
                      <div className="rounded-2xl border border-amber-200 bg-amber-50/35 p-4 space-y-4">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="text-[10px] font-black uppercase tracking-wider text-amber-800">Solicitação Ativa</p>
                            <p className="text-xs font-mono text-muted-foreground mt-0.5">{activeRequest.id.slice(0, 16)}...</p>
                          </div>
                          <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-black uppercase ${
                            activeRequest.status === 'pending' ? 'bg-amber-100 text-amber-800 border border-amber-200' :
                            activeRequest.status === 'approved' ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' :
                            activeRequest.status === 'executed' ? 'bg-blue-100 text-blue-800 border border-blue-200' :
                            'bg-rose-100 text-rose-800 border border-rose-200'
                          }`}>
                            {activeRequest.status}
                          </span>
                        </div>

                        <div className="space-y-1 text-xs text-muted-foreground">
                          <p><strong className="text-foreground">Solicitante:</strong> {activeRequest.requester}</p>
                          {activeRequest.approver && <p><strong className="text-foreground">Aprovador:</strong> {activeRequest.approver}</p>}
                          <p><strong className="text-foreground">Expira em:</strong> {new Date(activeRequest.expires_at).toLocaleTimeString()}</p>
                        </div>

                        {activeRequest.status === 'pending' && (
                          <div className="space-y-2">
                            <button
                              type="button"
                              onClick={() => approveRestoreRequest.mutate(activeRequest.id)}
                              disabled={approveRestoreRequest.isPending}
                              className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-black text-white transition-opacity hover:opacity-90 disabled:opacity-50 cursor-pointer"
                            >
                              <Check className="h-3.5 w-3.5 stroke-[3]" />
                              Aprovar Restore
                            </button>
                            <p className="text-[10px] text-center text-muted-foreground italic">
                              * Em produção, a autoaprovação é bloqueada.
                            </p>
                          </div>
                        )}

                        {activeRequest.status === 'approved' && (
                          <div className="space-y-3">
                            <div className="space-y-1">
                              <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">Token de Restore</label>
                              <input
                                type="text"
                                value={execToken}
                                onChange={(e) => setExecToken(e.target.value)}
                                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-amber-500"
                                placeholder="Digite ou cole o token"
                              />
                            </div>
                            <button
                              type="button"
                              onClick={() => executeRestoreRequest.mutate({ id: activeRequest.id, token: execToken })}
                              disabled={executeRestoreRequest.isPending || !execToken}
                              className="flex w-full items-center justify-center gap-2 rounded-xl bg-amber-600 px-4 py-2.5 text-xs font-black text-white transition-opacity hover:opacity-90 disabled:opacity-50 cursor-pointer"
                            >
                              <ArchiveRestore className="h-3.5 w-3.5" />
                              Executar Restore Real
                            </button>
                          </div>
                        )}

                        <button
                          type="button"
                          onClick={() => {
                            setActiveRequest(null)
                            setExecToken('')
                          }}
                          className="w-full text-center text-[10px] font-bold text-muted-foreground hover:text-foreground underline transition-colors cursor-pointer"
                        >
                          Limpar / Nova Solicitação
                        </button>
                      </div>
                    )}
                  </div>

                  {restoreResult && (
                    <div className="rounded-2xl border border-border bg-secondary/30 p-4 space-y-3 text-xs leading-relaxed">
                      <h3 className="font-bold text-foreground">Resultado do Restore/Rollback</h3>
                      <div className="space-y-1.5">
                        <p className="text-muted-foreground flex justify-between gap-4">
                          <span>Status final:</span>
                          <span className="font-bold text-foreground uppercase">{restoreResult.status}</span>
                        </p>
                        {restoreResult.details?.pre_restore_backup_id && (
                          <p className="text-muted-foreground flex justify-between gap-4">
                            <span>Backup de segurança:</span>
                            <span className="font-bold text-foreground font-mono">{restoreResult.details.pre_restore_backup_id}</span>
                          </p>
                        )}
                        {restoreResult.details?.rollback_status && restoreResult.details.rollback_status !== 'none' && (
                          <p className="text-muted-foreground flex justify-between gap-4">
                            <span>Status do rollback:</span>
                            <span className={`font-bold uppercase ${restoreResult.details.rollback_status === 'success' ? 'text-emerald-600' : 'text-rose-600'}`}>
                              {restoreResult.details.rollback_status}
                            </span>
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <p className="mt-4 text-sm text-muted-foreground">Selecione um backup para verificar ou restaurar.</p>
            )}
          </section>

          {/* Recent Failures Section */}
          <section className="rounded-3xl border border-border bg-card p-6 shadow-sm">
            <h2 className="text-lg font-black text-foreground mb-4">Falhas Operacionais Recentes</h2>
            {recentFailures.length > 0 ? (
              <div className="space-y-3">
                {recentFailures.slice(0, 5).map((fail) => (
                  <div key={fail.id} className="flex gap-3 rounded-2xl border border-rose-100 bg-rose-50/20 p-4 text-xs">
                    <AlertCircle className="h-5 w-5 text-rose-500 shrink-0" />
                    <div>
                      <p className="font-bold text-rose-950 flex justify-between gap-2">
                        <span>{fail.type} ({fail.target.slice(0, 15)})</span>
                        <span className="font-normal text-muted-foreground">{new Date(fail.timestamp).toLocaleTimeString()}</span>
                      </p>
                      <p className="mt-1 text-rose-700 font-semibold">{fail.error}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-6 text-center">
                <Check className="h-10 w-10 text-emerald-500 bg-emerald-50 rounded-full p-2 border border-emerald-100" />
                <p className="mt-2 text-xs font-semibold text-muted-foreground">Nenhuma falha operacional recente registrada.</p>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}

function MetricCard({ title, value, tone, subtitle }: { title: string; value: string; tone: 'good' | 'warn' | 'neutral'; subtitle?: string }) {
  const toneClass = tone === 'good' ? 'text-emerald-600' : tone === 'warn' ? 'text-amber-600' : 'text-foreground'
  return (
    <div className="rounded-3xl border border-border bg-card p-5 shadow-sm flex flex-col justify-between">
      <div>
        <p className="text-xs font-black uppercase tracking-[0.16em] text-muted-foreground">{title}</p>
        <p className={`mt-3 text-3xl font-black ${toneClass}`}>{value}</p>
      </div>
      {subtitle && (
        <p className="mt-2 text-xs font-medium text-muted-foreground border-t border-border/50 pt-2 flex items-center gap-1">
          <Clock className="h-3 w-3" /> {subtitle}
        </p>
      )}
    </div>
  )
}

function StatusPill({ status }: { status: string }) {
  const className =
    status === 'valid'
      ? 'bg-emerald-100 text-emerald-700'
      : status === 'corrupted'
        ? 'bg-rose-100 text-rose-700'
        : 'bg-amber-100 text-amber-700'
  return <span className={`rounded-full px-3 py-1 text-xs font-black uppercase ${className}`}>{status}</span>
}
