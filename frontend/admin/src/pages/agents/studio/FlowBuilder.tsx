import React, { useCallback, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Panel,
  MarkerType,
  Handle,
  Position,
} from '@xyflow/react';
import type {
  Connection,
  Edge,
  Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { CheckCircle2, Clock, Circle } from 'lucide-react';
import type { StudioFlowNode } from './studioData';

// Custom Node Component
const CustomNode = ({ data, isConnectable }: any) => {
  const { node } = data;
  return (
    <div className={`
      relative min-w-[200px] p-4 rounded-xl border transition-all
      ${data.selected 
        ? 'bg-blue-500/10 border-blue-500 shadow-[0_0_30px_rgba(59,130,246,0.15)]' 
        : 'bg-slate-900 border-slate-700 shadow-xl'}
    `}>
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} className="!w-3 !h-3 !bg-slate-800 !border-slate-500" />
      
      <div className="flex justify-between items-start mb-2">
        <span className={`
          text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded
          ${node.type === 'tool_call' ? 'text-purple-400 bg-purple-400/10' : 
            node.type === 'human_approval' ? 'text-amber-400 bg-amber-400/10' :
            node.type === 'end' ? 'text-emerald-400 bg-emerald-400/10' :
            'text-blue-400 bg-blue-400/10'}
        `}>
          {node.type.replace('_', ' ')}
        </span>
      </div>

      <h3 className="text-sm font-bold text-white mb-1">{node.label || node.type}</h3>
      <p className="text-[11px] text-slate-400 line-clamp-2">{node.config || 'No configuration'}</p>

      <Handle type="source" position={Position.Right} isConnectable={isConnectable} className="!w-3 !h-3 !bg-slate-800 !border-slate-500" />
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

interface FlowBuilderProps {
  nodes: StudioFlowNode[];
  onSelectNode: (id: string | null) => void;
}

export default function FlowBuilder({ nodes: initialNodes, onSelectNode }: FlowBuilderProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Sync initialNodes to React Flow nodes when it changes from parent
  useEffect(() => {
    const rfNodes: Node[] = initialNodes.map((n, idx) => ({
      id: n.id,
      type: 'custom',
      position: { x: 250 * idx, y: 150 }, // Auto layout horizontally initially
      data: { node: n },
    }));
    
    // Create sequential edges initially if empty
    const rfEdges: Edge[] = [];
    for (let i = 0; i < initialNodes.length - 1; i++) {
      rfEdges.push({
        id: `e-${initialNodes[i].id}-${initialNodes[i+1].id}`,
        source: initialNodes[i].id,
        target: initialNodes[i+1].id,
        markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' },
        style: { stroke: '#64748b', strokeWidth: 2 },
      });
    }

    setNodes(rfNodes);
    setEdges(rfEdges);
  }, [initialNodes, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ 
      ...params, 
      markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' as const },
    } as Edge, eds)),
    [setEdges]
  );

  const onSelectionChange = useCallback((params: any) => {
    if (params.nodes.length > 0) {
      onSelectNode(params.nodes[0].id);
    } else {
      onSelectNode(null);
    }
  }, [onSelectNode]);

  return (
    <div className="w-full h-full bg-[#020617]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onSelectionChange={onSelectionChange}
        nodeTypes={nodeTypes}
        fitView
        colorMode="dark"
      >
        <Background color="#1e293b" gap={16} size={1} />
        <Controls className="!bg-slate-900 !border-slate-800 !fill-white" />
        <MiniMap 
          nodeColor={(n) => '#3b82f6'} 
          maskColor="rgba(2, 6, 23, 0.8)"
          className="!bg-slate-900 !border-slate-800"
        />
        <Panel position="top-left" className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-800">
          Visual Workflow Builder
        </Panel>
      </ReactFlow>
    </div>
  );
}


