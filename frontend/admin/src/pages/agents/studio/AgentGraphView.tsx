import { useState, useCallback } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  PlayCircle,
  Square,
  RefreshCw,
  Download,
  AlertCircle,
  CheckCircle2,
  ListOrdered,
  GitBranch,
} from 'lucide-react'
import { toast } from 'sonner'
import api from '../../../lib/api'
import AgentGraphDag from '../../../components/agents/AgentGraphDag'
import type { DagNode, DagEdge } from '../../../components/agents/AgentGraphDag'

const NODE_TYPES = [
  { value: 'supervisor', label: 'Supervisor', color: '#3b82f6' },
  { value: 'worker', label: 'Worker', color: '#22c55e' },
  { value: 'reviewer', label: 'Reviewer', color: '#f59e0b' },
  { value: 'planner', label: 'Planner', color: '#8b5cf6' },
  { value: 'crew', label: 'Crew', color: '#ec4899' },
  { value: 'hierarchical', label: 'Hierarchical', color: '#14b8a6' },
]

export default function AgentGraphView() {
  const [nodes, setNodes] = useState<DagNode[]>([])
  const [edges, setEdges] = useState<DagEdge[]>([])
  const [selectedRun, setSelectedRun] = useState<string | null>(null)

  const runsQuery = useQuery({
    queryKey: ['agent-graph-runs'],
    queryFn: async () => (await api.get('/admin/agents/graphs/runs')).data,
    refetchInterval: 5000,
  })

  const runMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: `agent-graph-${Date.now()}`,
        nodes: nodes.map((n) => ({
          id: n.id,
          type: n.type,
          name: n.label,
          max_retries: 2,
          timeout_seconds: 300,
        })),
        edges: edges.map((e) => ({ source: e.source, target: e.target, condition: e.label })),
        max_concurrency: 5,
        enable_checkpointing: true,
      }
      return (await api.post('/admin/agents/graphs/run', payload)).data
    },
    onSuccess: (data) => {
      toast.success(`Graph run started: ${data.run_id}`)
      setSelectedRun(data.run_id)
      runsQuery.refetch()
    },
    onError: (err: any) => toast.error(err?.message || 'Failed to start graph'),
  })

  const cancelMutation = useMutation({
    mutationFn: async (runId: string) =>
      (await api.post(`/admin/agents/graphs/runs/${runId}/cancel`)).data,
    onSuccess: () => {
      toast.success('Graph run cancelled')
      runsQuery.refetch()
    },
    onError: (err: any) => toast.error(err?.message || 'Failed to cancel'),
  })

  const validateMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: 'validate',
        nodes: nodes.map((n) => ({ id: n.id, type: n.type, name: n.label })),
        edges: edges.map((e) => ({ source: e.source, target: e.target })),
      }
      return (await api.post('/admin/agents/graphs/validate', payload)).data
    },
    onSuccess: (data) => {
      toast.success(`Graph valid: ${data.node_count} nodes, ${data.edge_count} edges`)
    },
    onError: (err: any) => toast.error(err?.message || 'Validation failed'),
  })

  const selectedRunData = runsQuery.data?.find((r: any) => r.run_id === selectedRun)

  const addNode = useCallback((type: string) => {
    const id = `node-${Date.now()}`
    setNodes((prev) => [
      ...prev,
      { id, type, label: `${type.charAt(0).toUpperCase() + type.slice(1)} ${prev.length + 1}` },
    ])
  }, [])

  const addEdge = useCallback(() => {
    if (nodes.length < 2) {
      toast.error('Add at least 2 nodes first')
      return
    }
    const source = nodes[nodes.length - 2].id
    const target = nodes[nodes.length - 1].id
    if (edges.some((e) => e.source === source && e.target === target)) {
      toast.error('Edge already exists')
      return
    }
    setEdges((prev) => [...prev, { source, target }])
    toast.success(`Edge added: ${source} → ${target}`)
  }, [nodes, edges])

  const clearGraph = useCallback(() => {
    setNodes([])
    setEdges([])
    toast.success('Graph cleared')
  }, [])

  const dagNodes: DagNode[] = selectedRunData
    ? Object.entries(selectedRunData.node_results || {}).map(
        ([id, nr]: [string, any]) =>
          ({
            id,
            type: nr.node_id?.split('-')[0] || 'worker',
            label: nr.node_id || id,
            status: nr.status || 'pending',
            durationMs: nr.duration_ms,
          }) as DagNode,
      )
    : nodes

  const dagEdges: DagEdge[] = selectedRunData
    ? (() => {
        const ids = Object.keys(selectedRunData.node_results || {})
        return ids.slice(0, -1).map((src, i) => ({ source: src, target: ids[i + 1] }))
      })()
    : edges

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-primary" /> Agent Graph
          </h2>
          <p className="text-sm text-muted-foreground">
            DAG-based agent orchestration with parallel execution, retries, and checkpointing
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={clearGraph}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-sm font-medium hover:bg-accent"
          >
            <RefreshCw className="w-4 h-4" /> Clear
          </button>
          <button
            onClick={() => validateMutation.mutate()}
            disabled={validateMutation.isPending || nodes.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-sm font-medium hover:bg-accent disabled:opacity-50"
          >
            <ListOrdered className="w-4 h-4" /> Validate
          </button>
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending || nodes.length === 0}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-primary text-primary-foreground text-sm font-bold hover:opacity-90 disabled:opacity-50"
          >
            <PlayCircle className="w-4 h-4" /> Run Graph
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {NODE_TYPES.map((nt) => (
          <button
            key={nt.value}
            onClick={() => addNode(nt.value)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider border hover:opacity-80"
            style={{ borderColor: nt.color, color: nt.color }}
          >
            + {nt.label}
          </button>
        ))}
        <button
          onClick={addEdge}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider border border-border hover:bg-accent"
        >
          + Edge
        </button>
      </div>

      {validateMutation.data && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-green-500/10 border border-green-500/30 text-sm">
          <CheckCircle2 className="w-4 h-4 text-green-500" />
          Valid: {validateMutation.data.node_count} nodes, {validateMutation.data.edge_count} edges
          {validateMutation.data.topological_order && (
            <span className="font-mono text-xs text-muted-foreground ml-2">
              Order: {validateMutation.data.topological_order.join(' → ')}
            </span>
          )}
        </div>
      )}

      <AgentGraphDag nodes={dagNodes} edges={dagEdges} />

      {selectedRun && selectedRunData && (
        <div className="p-4 rounded-xl border border-border bg-card space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-bold">Run {selectedRunData.run_id?.slice(0, 8)}</h3>
            <div className="flex items-center gap-2">
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                  selectedRunData.status === 'completed'
                    ? 'bg-green-500/20 text-green-500'
                    : selectedRunData.status === 'failed'
                      ? 'bg-red-500/20 text-red-500'
                      : selectedRunData.status === 'running'
                        ? 'bg-blue-500/20 text-blue-500'
                        : 'bg-yellow-500/20 text-yellow-500'
                }`}
              >
                {selectedRunData.status}
              </span>
              <button
                onClick={() => cancelMutation.mutate(selectedRun)}
                className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-red-500/10 text-red-500 hover:bg-red-500/20"
              >
                <Square className="w-3 h-3" /> Cancel
              </button>
            </div>
          </div>
          {selectedRunData.error && (
            <div className="flex items-start gap-2 p-2 rounded bg-red-500/10 text-red-500 text-xs">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              {selectedRunData.error}
            </div>
          )}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {Object.entries(selectedRunData.node_results || {}).map(([id, nr]: [string, any]) => (
              <div key={id} className="p-2 rounded-lg bg-secondary/20 text-xs space-y-1">
                <div className="font-bold truncate">{nr.node_id}</div>
                <div className="text-muted-foreground">{nr.status}</div>
                {nr.duration_ms > 0 && (
                  <div className="font-mono text-muted-foreground">{nr.duration_ms.toFixed(0)}ms</div>
                )}
                {nr.retry_attempts > 0 && (
                  <div className="text-yellow-500">{nr.retry_attempts} retries</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-2">
        <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-wider">
          Previous Runs
        </h3>
        {runsQuery.data?.length === 0 && (
          <p className="text-sm text-muted-foreground">No runs yet</p>
        )}
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {(runsQuery.data || []).map((r: any) => (
            <button
              key={r.run_id}
              onClick={() => setSelectedRun(r.run_id)}
              className={`w-full flex items-center justify-between p-2 rounded-lg text-xs border transition-colors ${
                selectedRun === r.run_id
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:bg-accent'
              }`}
            >
              <span className="font-mono">{r.run_id?.slice(0, 12)}...</span>
              <span
                className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold ${
                  r.status === 'completed'
                    ? 'bg-green-500/20 text-green-500'
                    : r.status === 'failed'
                      ? 'bg-red-500/20 text-red-500'
                      : r.status === 'running'
                        ? 'bg-blue-500/20 text-blue-500'
                        : 'bg-yellow-500/20 text-yellow-500'
                }`}
              >
                {r.status}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
