import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArchiveRestore, ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import { JsonPanel, MetricCard, SectionCard, inputClassName } from '../../components/admin/AdminSurface'
import { LoadingCard } from '../../components/ui-feedback'
import api from '../../lib/api'

export default function ModelSupplyChain() {
  const queryClient = useQueryClient()
  const [entryId, setEntryId] = useState('')
  const [bundleId, setBundleId] = useState('')

  const statusQuery = useQuery({ queryKey: ['supply-chain-status'], queryFn: api.getSupplyChainStatus })
  const registryQuery = useQuery({ queryKey: ['supply-chain-registry'], queryFn: api.getSupplyChainRegistry })
  const provenanceQuery = useQuery({ queryKey: ['supply-chain-provenance'], queryFn: api.getSupplyChainProvenance })
  const bundlesQuery = useQuery({ queryKey: ['supply-chain-bundles'], queryFn: api.getSupplyChainBundles })
  const scansQuery = useQuery({ queryKey: ['integrity-scans'], queryFn: () => api.getIntegrityScans() })
  const eventsQuery = useQuery({ queryKey: ['integrity-events'], queryFn: () => api.getIntegrityEvents() })
  const attestationsQuery = useQuery({ queryKey: ['integrity-attestations'], queryFn: () => api.getIntegrityAttestations() })
  const integrityStatusQuery = useQuery({ queryKey: ['integrity-status'], queryFn: api.getIntegrityStatus })

  const actionMutation = useMutation({
    mutationFn: async ({ kind, id }: { kind: string; id: string }) => {
      if (kind === 'verify-entry') return api.verifySupplyChainEntry(id)
      if (kind === 'approve-entry') return api.approveSupplyChainEntry(id, { approved_by: 'admin' })
      if (kind === 'quarantine-entry') return api.quarantineSupplyChainEntry(id, { reason: 'manual quarantine', revoked_by: 'admin' })
      if (kind === 'revoke-entry') return api.revokeSupplyChainEntry(id, { reason: 'manual revoke', revocation_type: 'manual', revoked_by: 'admin' })
      if (kind === 'verify-bundle') return api.verifySupplyChainBundle(id)
      if (kind === 'promote-bundle') return api.promoteSupplyChainBundle(id)
      if (kind === 'reject-bundle') return api.rejectSupplyChainBundle(id, { reason: 'manual reject' })
      if (kind === 'integrity-quarantine') return api.quarantineIntegrityEntry(id)
      if (kind === 'integrity-reverify') return api.reverifyIntegrityEntry(id)
      return api.runIntegrityScan({ scan_type: 'manual' })
    },
    onSuccess: () => {
      toast.success('Acao executada.')
      queryClient.invalidateQueries({ queryKey: ['supply-chain-status'] })
      queryClient.invalidateQueries({ queryKey: ['supply-chain-registry'] })
      queryClient.invalidateQueries({ queryKey: ['supply-chain-bundles'] })
      queryClient.invalidateQueries({ queryKey: ['integrity-scans'] })
      queryClient.invalidateQueries({ queryKey: ['integrity-events'] })
      queryClient.invalidateQueries({ queryKey: ['integrity-status'] })
    },
    onError: (error: any) => toast.error(error.message || 'Falha na acao.'),
  })

  if (statusQuery.isLoading) return <LoadingCard />

  return (
    <div className="space-y-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Integrity Chain</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight text-foreground">Model Supply Chain</h1>
          <p className="mt-2 text-lg text-muted-foreground">Registry assinado, bundles de promocao, scans de integridade e attestation de runtime de modelos.</p>
        </div>
        <div className="rounded-3xl bg-primary/10 p-4 text-primary">
          <ArchiveRestore className="h-8 w-8" />
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Registry" value={String(statusQuery.data?.registry_total ?? 0)} />
        <MetricCard label="Bundles" value={String(statusQuery.data?.bundle_total ?? 0)} />
        <MetricCard label="Revocations" value={String(statusQuery.data?.revocation_total ?? 0)} />
        <MetricCard label="Enforcement" value={String(statusQuery.data?.enforcement_mode ?? 'n/a')} />
      </div>

      <SectionCard title="Status" subtitle="Resumo consolidado da cadeia de suprimento.">
        <JsonPanel data={statusQuery.data} />
      </SectionCard>

      <SectionCard title="Entry Actions" subtitle="Operacoes em entradas do registry e bundles.">
        <div className="grid gap-3 md:grid-cols-2">
          <input value={entryId} onChange={event => setEntryId(event.target.value)} className={inputClassName} placeholder="entry_id" />
          <input value={bundleId} onChange={event => setBundleId(event.target.value)} className={inputClassName} placeholder="bundle_id" />
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <button onClick={() => actionMutation.mutate({ kind: 'verify-entry', id: entryId })} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Verify Entry</button>
          <button onClick={() => actionMutation.mutate({ kind: 'approve-entry', id: entryId })} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Approve Entry</button>
          <button onClick={() => actionMutation.mutate({ kind: 'quarantine-entry', id: entryId })} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Quarantine Entry</button>
          <button onClick={() => actionMutation.mutate({ kind: 'revoke-entry', id: entryId })} className="rounded-2xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100">Revoke Entry</button>
          <button onClick={() => actionMutation.mutate({ kind: 'verify-bundle', id: bundleId })} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Verify Bundle</button>
          <button onClick={() => actionMutation.mutate({ kind: 'promote-bundle', id: bundleId })} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Promote Bundle</button>
          <button onClick={() => actionMutation.mutate({ kind: 'reject-bundle', id: bundleId })} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Reject Bundle</button>
          <button onClick={() => actionMutation.mutate({ kind: 'run-scan', id: '' })} className="inline-flex items-center gap-2 rounded-2xl bg-foreground px-4 py-2 text-sm font-semibold text-background">
            <ShieldCheck className="h-4 w-4" />
            Run Integrity Scan
          </button>
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Registry" subtitle="Entradas assinadas e trust state.">
          <JsonPanel data={registryQuery.data} />
        </SectionCard>
        <SectionCard title="Provenance" subtitle="Attestations de origem do modelo.">
          <JsonPanel data={provenanceQuery.data} />
        </SectionCard>
        <SectionCard title="Bundles" subtitle="Bundles de promocao entre clusters.">
          <JsonPanel data={bundlesQuery.data} />
        </SectionCard>
        <SectionCard title="Integrity Status" subtitle="Status consolidado de scans e enforcement.">
          <JsonPanel data={integrityStatusQuery.data} />
        </SectionCard>
        <SectionCard title="Integrity Scans" subtitle="Historico de scans.">
          <JsonPanel data={scansQuery.data} />
        </SectionCard>
        <SectionCard title="Integrity Events" subtitle="Eventos e violacoes de integridade.">
          <JsonPanel data={eventsQuery.data} />
        </SectionCard>
        <SectionCard title="Runtime Model Attestations" subtitle="Attestations de runtime dos modelos.">
          <JsonPanel data={attestationsQuery.data} />
        </SectionCard>
      </div>
    </div>
  )
}
