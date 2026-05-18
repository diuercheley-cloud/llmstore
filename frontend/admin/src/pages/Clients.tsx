import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import { Plus, Search, ShieldCheck, ShieldAlert, MoreHorizontal, Edit, Ban } from 'lucide-react'
import { useState } from 'react'

interface Client {
  id: string
  name: string
  billing_plan_id: string
  billing_status: string
  is_blocked: boolean
  rate_limit_per_minute: number
  daily_token_quota: number
  created_at: string
}

export default function Clients() {
  const [search, setSearch] = useState('')
  const { data: clients, isLoading } = useQuery<Client[]>({
    queryKey: ['clients'],
    queryFn: async () => {
      const res = await api.get('/admin/clients')
      return res.data
    }
  })

  const filtered = clients?.filter(c => 
    c.name.toLowerCase().includes(search.toLowerCase()) || 
    c.id.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Gestão de Clientes</h1>
          <p className="text-slate-500">Controle de acesso, quotas e faturamento por tenant.</p>
        </div>
        <button className="bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-xl font-bold flex items-center gap-2 transition-colors">
          <Plus className="w-5 h-5" />
          Novo Cliente
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex gap-4">
          <div className="relative flex-1">
            <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              placeholder="Buscar por nome ou ID..."
              className="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-500 outline-none"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-slate-500 text-sm font-semibold bg-slate-50">
                <th className="px-6 py-4">Cliente</th>
                <th className="px-6 py-4">Plano / Billing</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Quotas (RPM/Dia)</th>
                <th className="px-6 py-4">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading && (
                <tr><td colSpan={5} className="px-6 py-12 text-center text-slate-400">Carregando clientes...</td></tr>
              )}
              {filtered?.map(client => (
                <tr key={client.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-bold text-slate-900">{client.name}</div>
                    <div className="text-xs font-mono text-slate-400">{client.id}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium">{client.billing_plan_id || 'Plano Padrão'}</div>
                    <div className="text-xs text-slate-400">billing: {client.billing_status}</div>
                  </td>
                  <td className="px-6 py-4">
                    {client.is_blocked ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 text-xs font-bold rounded-md">
                        <ShieldAlert className="w-3 h-3" /> BLOQUEADO
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-md">
                        <ShieldCheck className="w-3 h-3" /> ATIVO
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <div className="text-slate-700 font-medium">{client.rate_limit_per_minute.toLocaleString()} RPM</div>
                    <div className="text-slate-400 text-xs">{client.daily_token_quota.toLocaleString()} tokens/dia</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button className="p-2 hover:bg-slate-200 rounded-lg text-slate-600 transition-colors"><Edit className="w-4 h-4" /></button>
                      <button className="p-2 hover:bg-red-50 rounded-lg text-red-600 transition-colors"><Ban className="w-4 h-4" /></button>
                      <button className="p-2 hover:bg-slate-200 rounded-lg text-slate-600 transition-colors"><MoreHorizontal className="w-4 h-4" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
