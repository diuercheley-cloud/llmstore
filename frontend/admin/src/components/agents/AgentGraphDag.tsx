import { useMemo, useCallback } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
  MarkerType,
} from '@xyflow/react'
import type { ReactNode } from 'react'
import '@xyflow/react/dist/style.css'
import { Bot, Users, Eye, ClipboardList, Shield, GitBranch } from 'lucide-react'

const AGENT_COLORS: Record<string, string> = {
  supervisor: '#3b82f6',
  worker: '#22c55e',
  reviewer: '#f59e0b',
  planner: '#8b5cf6',
  crew: '#ec4899',
  hierarchical: '#14b8a6',
}

const AGENT_ICONS: Record<string, ReactNode> = {
  supervisor: <Shield className="w-5 h-5" />,
  worker: <Bot className="w-5 h-5" />,
  reviewer: <Eye className="w-5 h-5" />,
  planner: <ClipboardList className="w-5 h-5" />,
  crew: <Users className="w-5 h-5" />,
  hierarchical: <GitBranch className="w-5 h-5" />,
}

interface AgentGraphNodeData extends Record<string, unknown> {
  nodeType: string
  label: string
  status: string
  durationMs?: number
}

function AgentGraphNode({ data }: NodeProps<Node<AgentGraphNodeData>>) {
  const color = AGENT_COLORS[data.nodeType] || '#6b7280'
  const icon = AGENT_ICONS[data.nodeType]

  return (
    <div
      className="rounded-xl border-2 shadow-lg bg-card min-w-[180px]"
      style={{ borderColor: color }}
    >
      <Handle type="target" position={Position.Left} className="!bg-border" />
      <div className="p-4 space-y-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg" style={{ backgroundColor: `${color}20`, color }}>
            {icon}
          </div>
          <div>
            <div className="text-xs font-bold uppercase tracking-wider" style={{ color }}>
              {data.nodeType}
            </div>
            <div className="text-sm font-bold">{data.label}</div>
          </div>
        </div>
        <div className="text-xs text-muted-foreground">
          {data.status === 'running' && <span className="text-blue-500">● Running</span>}
          {data.status === 'completed' && <span className="text-green-500">✓ Completed</span>}
          {data.status === 'failed' && <span className="text-red-500">✗ Failed</span>}
          {data.status === 'pending' && <span className="text-muted-foreground">○ Pending</span>}
          {data.status === 'cancelled' && <span className="text-yellow-500">⊙ Cancelled</span>}
        </div>
        {typeof data.durationMs === 'number' && (
          <div className="text-[10px] text-muted-foreground font-mono">
            {data.durationMs.toFixed(0)}ms
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-border" />
    </div>
  )
}

const nodeTypes = { agentGraphNode: AgentGraphNode }

export interface DagNode {
  id: string
  type: string
  label: string
  status?: string
  durationMs?: number
}

export interface DagEdge {
  source: string
  target: string
  label?: string
}

interface Props {
  nodes: DagNode[]
  edges: DagEdge[]
  onNodeClick?: (nodeId: string) => void
}

export default function AgentGraphDag({ nodes: inputNodes, edges: inputEdges, onNodeClick }: Props) {
  const initialNodes: Node<AgentGraphNodeData>[] = useMemo(
    () =>
      inputNodes.map((n, idx) => ({
        id: n.id,
        type: 'agentGraphNode',
        position: { x: idx * 220, y: 0 },
        data: {
          nodeType: n.type,
          label: n.label,
          status: n.status || 'pending',
          durationMs: n.durationMs,
        },
      })),
    [inputNodes],
  )

  const initialEdges: Edge[] = useMemo(
    () =>
      inputEdges.map((e) => ({
        id: `${e.source}-${e.target}`,
        source: e.source,
        target: e.target,
        label: e.label,
        animated: true,
        style: { stroke: '#64748b', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' },
      })),
    [inputEdges],
  )

  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [rfEdges, , onEdgesChange] = useEdgesState(initialEdges)

  const onNodeClickHandler = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.id)
    },
    [onNodeClick],
  )

  return (
    <div className="w-full h-[500px] rounded-xl border border-border overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={rfEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClickHandler}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background color="#94a3b8" gap={20} size={1} />
        <Controls />
        <MiniMap
          nodeStrokeColor="#64748b"
          nodeColor={(n) => {
            const nodeType = typeof n.data?.nodeType === 'string' ? n.data.nodeType : ''
            return AGENT_COLORS[nodeType] || '#94a3b8'
          }}
          maskColor="rgba(0,0,0,0.1)"
        />
      </ReactFlow>
    </div>
  )
}
