import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { Cpu, Server, Activity, Database, MoreVertical, LogOut, ArrowDownToLine } from 'lucide-react'
import StatusBadge from '../../components/operations/StatusBadge'
import { useState } from 'react'
import ConfirmDangerActionModal from '../../components/operations/ConfirmDangerActionModal'

export default function RuntimeNodes() {
  const queryClient = useQueryClient()
  const [selectedNode, setSelectedNode] = useState<string | null>(null)

  const { data: nodes, isLoading } = useQuery({
    queryKey: ['runtime-nodes'],
    queryFn: async () => {
      const res = await api.get('/admin/operations/runtime-nodes')
      return res.data
    },
    refetchInterval: 10000
  })

  const drainMutation = useMutation({
    mutationFn: async (nodeId: string) => {
      return api.post(`/admin/operations/nodes/${nodeId}/drain`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runtime-nodes'] })
      setSelectedNode(null)
    }
  })

  if (isLoading) return <div className="p-8">Carregando nós...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-black text-slate-900 mb-2">Runtime <span className="text-teal-600">Nodes</span></h1>
          <p className="text-slate-500 font-medium">Gestão de infraestrutura de execução e balanceamento de carga.</p>
        </div>
        <div className="flex gap-4">
           <div className="bg-white px-4 py-2 rounded-xl border border-slate-200 shadow-sm flex items-center gap-2">
             <div className="w-2 h-2 bg-green-500 rounded-full"></div>
             <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">{nodes?.length || 0} Nós Ativos</span>
           </div>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden">
        <table className="w-full text-left">
          <thead>
            <tr className="bg-slate-50/50 text-slate-400 text-[10px] font-black uppercase tracking-widest border-b border-slate-100">
              <th className="px-6 py-4">Node Identity</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Resource Usage</th>
              <th className="px-6 py-4">Role</th>
              <th className="px-6 py-4">Last Heartbeat</th>
              <th className="px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {nodes?.map((node: any) => (
              <tr key={node.id} className="hover:bg-slate-50/50 transition-colors group">
                <td className="px-6 py-5">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-100 text-slate-500 rounded-lg group-hover:bg-teal-50 group-hover:text-teal-600 transition-colors">
                      <Server className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-bold text-slate-900">{node.name}</div>
                      <div className="text-[10px] font-mono text-slate-400 uppercase tracking-tighter">{node.id} • {node.version}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-5">
                  <StatusBadge status={node.status} />
                </td>
                <td className="px-6 py-5">
                  <div className="space-y-1.5 w-40">
                    <div className="flex justify-between text-[9px] font-bold text-slate-400 uppercase">
                      <span>CPU</span>
                      <span>{node.cpu_usage}%</span>
                    </div>
                    <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
                      <div className="bg-teal-500 h-full" style={{ width: `${node.cpu_usage}%` }}></div>
                    </div>
                    <div className="flex justify-between text-[9px] font-bold text-slate-400 uppercase">
                      <span>MEM</span>
                      <span>{node.memory_usage}%</span>
                    </div>
                    <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
                      <div className="bg-amber-500 h-full" style={{ width: `${node.memory_usage}%` }}></div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-5">
                  <span className="px-2 py-1 bg-slate-100 text-slate-600 text-[10px] font-black uppercase rounded tracking-wider">
                    {node.role}
                  </span>
                </td>
                <td className="px-6 py-5">
                  <div className="text-xs font-medium text-slate-500">{new Date(node.last_heartbeat).toLocaleTimeString()}</div>
                </td>
                <td className="px-6 py-5">
                  <div className="flex gap-2">
                    <button 
                      onClick={() => setSelectedNode(node.id)}
                      disabled={node.status === 'draining'}
                      className="p-2 hover:bg-rose-50 text-slate-400 hover:text-rose-600 rounded-xl transition-all disabled:opacity-30"
                      title="Drain Node"
                    >
                      <ArrowDownToLine className="w-4 h-4" />
                    </button>
                    <button className="p-2 hover:bg-slate-100 text-slate-400 hover:text-slate-900 rounded-xl transition-all">
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ConfirmDangerActionModal 
        isOpen={!!selectedNode}
        onClose={() => setSelectedNode(null)}
        onConfirm={() => selectedNode && drainMutation.mutate(selectedNode)}
        title="Colocar Nó em Drain"
        description="Esta ação impedirá que novas requisições sejam enviadas para este nó. As requisições em andamento serão concluídas antes que o nó seja marcado como inativo. Útil para manutenção programada."
        confirmLabel="Iniciar Drain"
        isPending={drainMutation.isPending}
      />
    </div>
  )
}
