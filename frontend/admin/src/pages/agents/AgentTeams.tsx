import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Play, Users } from 'lucide-react'
import { toast } from 'sonner'
import { JsonPanel, MetricCard, SectionCard, inputClassName } from '../../components/admin/AdminSurface'
import { LoadingCard } from '../../components/ui-feedback'
import api from '../../lib/api'

export default function AgentTeams() {
  const [teamName, setTeamName] = useState('')
  const [topology, setTopology] = useState('hierarchical')
  const [selectedTeamId, setSelectedTeamId] = useState('')
  const [goal, setGoal] = useState('')
  const [runId, setRunId] = useState('')

  const teamsQuery = useQuery({ queryKey: ['agent-teams'], queryFn: api.listAgentTeams })
  const createMutation = useMutation({
    mutationFn: () => api.createAgentTeam({ name: teamName, topology, owner_user_id: 'admin', members: [] }),
    onSuccess: () => {
      toast.success('Team criado.')
      teamsQuery.refetch()
    },
    onError: (error: any) => toast.error(error.message || 'Falha ao criar team.'),
  })
  const runMutation = useMutation({
    mutationFn: () => api.runAgentTeam(selectedTeamId, { goal, work_items: [] }),
    onError: (error: any) => toast.error(error.message || 'Falha ao executar team.'),
  })
  const traceQuery = useQuery({ queryKey: ['agent-team-trace', runId], queryFn: () => api.getAgentTeamTrace(runId), enabled: Boolean(runId) })

  if (teamsQuery.isLoading) return <LoadingCard />

  return (
    <div className="space-y-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Multi-Agent</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight text-foreground">Agent Teams</h1>
          <p className="mt-2 text-lg text-muted-foreground">Cria times multiagente, dispara runs e consulta traces do runtime de equipe.</p>
        </div>
        <div className="rounded-3xl bg-primary/10 p-4 text-primary">
          <Users className="h-8 w-8" />
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Teams" value={String((teamsQuery.data ?? []).length)} />
        <MetricCard label="Topology" value={topology} />
        <MetricCard label="Trace Loaded" value={traceQuery.data ? 'yes' : 'no'} />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Create Team" subtitle="POST /admin/agents/teams">
          <div className="grid gap-3">
            <input value={teamName} onChange={event => setTeamName(event.target.value)} className={inputClassName} placeholder="Nome do team" />
            <select value={topology} onChange={event => setTopology(event.target.value)} className={inputClassName}>
              <option value="hierarchical">hierarchical</option>
              <option value="debate">debate</option>
              <option value="dynamic">dynamic</option>
            </select>
            <button onClick={() => createMutation.mutate()} className="rounded-2xl bg-foreground px-4 py-2 text-sm font-semibold text-background">Create</button>
          </div>
        </SectionCard>

        <SectionCard title="Run Team" subtitle="POST /admin/agents/teams/{id}/runs">
          <div className="grid gap-3">
            <select value={selectedTeamId} onChange={event => setSelectedTeamId(event.target.value)} className={inputClassName}>
              <option value="">Selecione um team</option>
              {(teamsQuery.data ?? []).map((team: any) => (
                <option key={team.id} value={team.id}>{team.name}</option>
              ))}
            </select>
            <textarea value={goal} onChange={event => setGoal(event.target.value)} className={`${inputClassName} min-h-28`} placeholder="Objetivo do time" />
            <button onClick={() => runMutation.mutate()} disabled={!selectedTeamId} className="inline-flex items-center gap-2 rounded-2xl border border-border px-4 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-50">
              <Play className="h-4 w-4" />
              Run
            </button>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Teams Catalog" subtitle="Listagem atual.">
        <JsonPanel data={teamsQuery.data} />
      </SectionCard>

      <SectionCard title="Run Trace" subtitle="Trace do run multiagente por run_id.">
        <div className="mb-4">
          <input value={runId} onChange={event => setRunId(event.target.value)} className={inputClassName} placeholder="run_id para trace" />
        </div>
        <JsonPanel data={traceQuery.data} empty="Informe um run_id para carregar o trace." />
      </SectionCard>
    </div>
  )
}
