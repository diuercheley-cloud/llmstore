import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import { JsonPanel, MetricCard, SectionCard, inputClassName } from '../../components/admin/AdminSurface'
import { LoadingCard } from '../../components/ui-feedback'
import api from '../../lib/api'

export default function Attestation() {
  const [attestationId, setAttestationId] = useState('')
  const [challengeId, setChallengeId] = useState('')

  const summaryQuery = useQuery({ queryKey: ['attestation-summary'], queryFn: api.getAttestationSummary })
  const attestationsQuery = useQuery({ queryKey: ['attestations'], queryFn: api.listAttestations })
  const evidenceQuery = useQuery({ queryKey: ['attestation-evidence'], queryFn: api.listAttestationEvidence })
  const challengesQuery = useQuery({ queryKey: ['attestation-challenges'], queryFn: api.listAttestationChallenges })
  const driftQuery = useQuery({ queryKey: ['attestation-drift'], queryFn: api.listAttestationDrift })

  const verifyMutation = useMutation({ mutationFn: () => api.verifyAttestation(attestationId) })
  const trustScoreMutation = useMutation({ mutationFn: () => api.computeAttestationTrustScore(attestationId) })
  const driftMutation = useMutation({ mutationFn: () => api.detectAttestationDrift(attestationId, { runtime_hash: 'updated-runtime-hash' }) })
  const revokeMutation = useMutation({ mutationFn: () => api.revokeAttestation(attestationId, { reason: 'manual revoke' }) })
  const issueChallengeMutation = useMutation({
    mutationFn: () => api.issueAttestationChallenge({ cluster_id: 'default', challenge_type: 'runtime_measurement' }),
    onSuccess: () => challengesQuery.refetch(),
    onError: (error: any) => toast.error(error.message || 'Falha ao emitir challenge.'),
  })
  const respondChallengeMutation = useMutation({ mutationFn: () => api.respondAttestationChallenge(challengeId, { response_data: { status: 'ok' } }) })

  if (summaryQuery.isLoading) return <LoadingCard />

  return (
    <div className="space-y-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Trusted Runtime</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight text-foreground">Attestation</h1>
          <p className="mt-2 text-lg text-muted-foreground">Runtime summary, evidence, drift, challenges e trust score do ambiente atestado.</p>
        </div>
        <div className="rounded-3xl bg-primary/10 p-4 text-primary">
          <ShieldCheck className="h-8 w-8" />
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Runtime Records" value={String((attestationsQuery.data ?? []).length)} />
        <MetricCard label="Evidence" value={String((evidenceQuery.data ?? []).length)} />
        <MetricCard label="Challenges" value={String((challengesQuery.data ?? []).length)} />
        <MetricCard label="Drift Events" value={String((driftQuery.data ?? []).length)} />
      </div>

      <SectionCard title="Runtime Summary" subtitle="GET /admin/attestation/runtime/summary">
        <JsonPanel data={summaryQuery.data} />
      </SectionCard>

      <SectionCard title="Actions" subtitle="Verify, trust score, drift, revoke e challenge flow.">
        <div className="grid gap-3 md:grid-cols-2">
          <input value={attestationId} onChange={event => setAttestationId(event.target.value)} className={inputClassName} placeholder="attestation_id" />
          <input value={challengeId} onChange={event => setChallengeId(event.target.value)} className={inputClassName} placeholder="challenge_id" />
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <button onClick={() => verifyMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Verify</button>
          <button onClick={() => trustScoreMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Trust Score</button>
          <button onClick={() => driftMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Detect Drift</button>
          <button onClick={() => revokeMutation.mutate()} className="rounded-2xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100">Revoke</button>
          <button onClick={() => issueChallengeMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Issue Challenge</button>
          <button onClick={() => respondChallengeMutation.mutate()} className="rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">Respond Challenge</button>
        </div>
        <div className="mt-4">
          <JsonPanel data={respondChallengeMutation.data ?? issueChallengeMutation.data ?? revokeMutation.data ?? driftMutation.data ?? trustScoreMutation.data ?? verifyMutation.data} empty="Execute uma acao para ver o retorno." />
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Runtime Attestations" subtitle="Lista operacional do runtime."><JsonPanel data={attestationsQuery.data} /></SectionCard>
        <SectionCard title="Evidence" subtitle="Evidence chain e hashes coletados."><JsonPanel data={evidenceQuery.data} /></SectionCard>
        <SectionCard title="Challenges" subtitle="Challenges emitidos e respostas."><JsonPanel data={challengesQuery.data} /></SectionCard>
        <SectionCard title="Drift" subtitle="Eventos com drift detectado."><JsonPanel data={driftQuery.data} /></SectionCard>
      </div>
    </div>
  )
}
