import { useMemo, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Play, Save, Wand2, Workflow } from 'lucide-react'
import { toast } from 'sonner'

import api from '../../../lib/api'

const DEFAULT_GRAPH = {
  nodes: [
    {
      id: 'start',
      node_type: 'model_call',
      data: { label: 'Model Call' },
      config: { model: 'default' },
    },
  ],
  edges: [],
}

export default function AgentStudio() {
  const queryClient = useQueryClient()
  const [flowName, setFlowName] = useState('')
  const [flowDescription, setFlowDescription] = useState('')
  const [graphJson, setGraphJson] = useState(JSON.stringify(DEFAULT_GRAPH, null, 2))
  const [selectedFlowId, setSelectedFlowId] = useState('')
  const [versionLabel, setVersionLabel] = useState('draft-1')
  const [runPayload, setRunPayload] = useState('{\n  "input": "hello"\n}')

  const { data: flows = [] } = useQuery({
    queryKey: ['studio-flows'],
    queryFn: () => api.listStudioFlows(),
  })

  const selectedFlow = flows.find((flow: any) => String(flow.id) === selectedFlowId) || null

  const { data: flowDetail } = useQuery({
    queryKey: ['studio-flow-detail', selectedFlowId],
    queryFn: () => selectedFlowId ? api.getStudioFlow(selectedFlowId) : null,
    enabled: !!selectedFlowId,
  })

  const { data: templates } = useQuery({
    queryKey: ['studio-templates'],
    queryFn: () => api.listStudioTemplates(),
  })

  const createFlowMutation = useMutation({
    mutationFn: () => api.createStudioFlow({
      name: flowName.trim(),
      description: flowDescription.trim() || null,
      graph_json: parseJson(graphJson),
      permissions: [],
      required_capabilities: [],
      risk_level: 'low',
    }),
    onSuccess: (result: any) => {
      toast.success('Flow criado.')
      queryClient.invalidateQueries({ queryKey: ['studio-flows'] })
      if (result?.id) setSelectedFlowId(String(result.id))
    },
    onError: (error: any) => toast.error(error?.message || 'Falha ao criar flow'),
  })

  const saveVersionMutation = useMutation({
    mutationFn: () => api.saveStudioFlowVersion(selectedFlowId, {
      graph: parseJson(graphJson),
      label: versionLabel.trim(),
      make_active: true,
    }),
    onSuccess: () => {
      toast.success('Versao salva.')
      queryClient.invalidateQueries({ queryKey: ['studio-flow-detail', selectedFlowId] })
    },
    onError: (error: any) => toast.error(error?.message || 'Falha ao salvar versao'),
  })

  const validateFlowMutation = useMutation({
    mutationFn: () => api.validateStudioFlow(selectedFlowId),
    onError: (error: any) => toast.error(error?.message || 'Falha na validacao'),
  })

  const compileFlowMutation = useMutation({
    mutationFn: () => api.compileStudioFlow(selectedFlowId),
    onError: (error: any) => toast.error(error?.message || 'Falha na compilacao'),
  })

  const explainFlowMutation = useMutation({
    mutationFn: () => api.explainStudioFlow(selectedFlowId),
    onError: (error: any) => toast.error(error?.message || 'Falha ao explicar flow'),
  })

  const dryRunMutation = useMutation({
    mutationFn: () => api.dryRunStudioFlow(selectedFlowId, parseJson(runPayload)),
    onError: (error: any) => toast.error(error?.message || 'Falha no dry-run'),
  })

  const deployMutation = useMutation({
    mutationFn: () => api.deployStudioFlow(selectedFlowId, parseJson(runPayload)),
    onSuccess: () => toast.success('Deploy do flow executado.'),
    onError: (error: any) => toast.error(error?.message || 'Falha no deploy'),
  })

  const versionList = useMemo(() => {
    const activeVersion = flowDetail?.active_version
    return activeVersion ? [activeVersion] : []
  }, [flowDetail])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-foreground">Agent Studio</h1>
        <p className="text-sm md:text-lg text-muted-foreground">Painel funcional de flows reais: create, version, validate, compile, explain, dry-run e deploy.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr,1.05fr]">
        <Card title="Novo Flow">
          <div className="space-y-4">
            <label className="space-y-2">
              <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Nome</span>
              <input value={flowName} onChange={e => setFlowName(e.target.value)} className={inputClassName} />
            </label>
            <label className="space-y-2">
              <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Descricao</span>
              <input value={flowDescription} onChange={e => setFlowDescription(e.target.value)} className={inputClassName} />
            </label>
            <label className="space-y-2">
              <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Graph JSON</span>
              <textarea value={graphJson} onChange={e => setGraphJson(e.target.value)} className={`${inputClassName} min-h-[240px] font-mono text-xs`} />
            </label>
            <button type="button" onClick={() => createFlowMutation.mutate()} disabled={!flowName.trim()} className="rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:bg-primary/90 disabled:opacity-50">
              <Workflow className="mr-2 inline h-4 w-4" />
              Criar Flow
            </button>
          </div>
        </Card>

        <Card title="Flows Registrados">
          <div className="space-y-4">
            <select value={selectedFlowId} onChange={e => setSelectedFlowId(e.target.value)} className={inputClassName}>
              <option value="">Selecione um flow</option>
              {flows.map((flow: any) => (
                <option key={flow.id} value={String(flow.id)}>
                  {flow.name}
                </option>
              ))}
            </select>

            {selectedFlow ? (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <DetailCard label="Flow" value={selectedFlow.name} />
                  <DetailCard label="Descricao" value={selectedFlow.description || '-'} />
                </div>

                <label className="space-y-2">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Nova versao</span>
                  <input value={versionLabel} onChange={e => setVersionLabel(e.target.value)} className={inputClassName} />
                </label>

                <label className="space-y-2">
                  <span className="text-xs font-black uppercase tracking-widest text-muted-foreground">Payload de run</span>
                  <textarea value={runPayload} onChange={e => setRunPayload(e.target.value)} className={`${inputClassName} min-h-[120px] font-mono text-xs`} />
                </label>

                <div className="flex flex-wrap gap-3">
                  <button type="button" onClick={() => saveVersionMutation.mutate()} className="rounded-xl border border-border px-4 py-2 text-sm font-bold hover:bg-secondary">
                    <Save className="mr-2 inline h-4 w-4" />
                    Salvar versao
                  </button>
                  <button type="button" onClick={() => validateFlowMutation.mutate()} className="rounded-xl border border-border px-4 py-2 text-sm font-bold hover:bg-secondary">
                    <CheckCircle2 className="mr-2 inline h-4 w-4" />
                    Validar
                  </button>
                  <button type="button" onClick={() => compileFlowMutation.mutate()} className="rounded-xl border border-border px-4 py-2 text-sm font-bold hover:bg-secondary">
                    Compilar
                  </button>
                  <button type="button" onClick={() => explainFlowMutation.mutate()} className="rounded-xl border border-border px-4 py-2 text-sm font-bold hover:bg-secondary">
                    <Wand2 className="mr-2 inline h-4 w-4" />
                    Explain
                  </button>
                  <button type="button" onClick={() => dryRunMutation.mutate()} className="rounded-xl border border-border px-4 py-2 text-sm font-bold hover:bg-secondary">
                    Dry-run
                  </button>
                  <button type="button" onClick={() => deployMutation.mutate()} className="rounded-xl bg-primary px-4 py-2 text-sm font-bold text-white hover:bg-primary/90">
                    <Play className="mr-2 inline h-4 w-4" />
                    Deploy
                  </button>
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                  <Panel title="Active Version">
                    <JsonBlock value={versionList} />
                  </Panel>
                  <Panel title="Templates">
                    <JsonBlock value={templates?.templates || templates || []} />
                  </Panel>
                  <Panel title="Validate Result">
                    <JsonBlock value={validateFlowMutation.data} />
                  </Panel>
                  <Panel title="Compile Result">
                    <JsonBlock value={compileFlowMutation.data} />
                  </Panel>
                  <Panel title="Explain Result">
                    <JsonBlock value={explainFlowMutation.data} />
                  </Panel>
                  <Panel title="Dry-run / Deploy">
                    <JsonBlock value={dryRunMutation.data || deployMutation.data} />
                  </Panel>
                </div>
              </>
            ) : (
              <div className="rounded-2xl border border-dashed border-border p-6 text-sm text-muted-foreground">Selecione um flow para operar.</div>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}

function parseJson(raw: string) {
  try {
    return JSON.parse(raw)
  } catch {
    throw new Error('JSON invalido')
  }
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-3xl border border-border bg-card p-5 shadow-sm">
      <div className="mb-4 text-lg font-black text-foreground">{title}</div>
      {children}
    </section>
  )
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-background p-4">
      <div className="mb-3 text-xs font-black uppercase tracking-widest text-muted-foreground">{title}</div>
      {children}
    </div>
  )
}

function DetailCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border bg-background p-3">
      <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm font-semibold text-foreground">{value}</div>
    </div>
  )
}

function JsonBlock({ value }: { value: any }) {
  return (
    <pre className="overflow-x-auto rounded-2xl bg-card p-3 text-[10px] text-foreground">
      {JSON.stringify(value || {}, null, 2)}
    </pre>
  )
}

const inputClassName = 'w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none focus:border-primary'
