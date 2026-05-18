import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import { Cpu, Server, Activity, Plus, Search, CheckCircle2, AlertCircle, Terminal, Info } from 'lucide-react'
import { useState } from 'react'

interface Backend {
  id: string
  name: string
  base_url: string
  is_enabled: boolean
  is_active: boolean
  provider_type: string
  max_concurrency: number
}

export default function Backends() {
  const [search, setSearch] = useState('')

  const { data: backends, isLoading } = useQuery<Backend[]>({
    queryKey: ['backends'],
    queryFn: async () => {
      const res = await api.get('/admin/backends')
      return res.data
    }
  })

  const filtered = backends?.filter(b => 
    b.name.toLowerCase().includes(search.toLowerCase()) || 
    b.id.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Backends / Providers</h1>
          <p className="text-slate-500">Gestão de clusters de inferência, providers externos e saúde do runtime.</p>
        </div>
        <div className="flex gap-3">
          <button className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-xl font-bold transition-colors">
            Testar Conexões
          </button>
          <button className="bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-xl font-bold flex items-center gap-2 transition-colors shadow-lg shadow-teal-600/20">
            <Plus className="w-5 h-5" />
            Adicionar Backend
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-teal-50 text-teal-600 rounded-xl"><Server className="w-6 h-6" /></div>
          <div>
            <div className="text-slate-400 text-xs font-bold uppercase tracking-wider">Backends Ativos</div>
            <div className="text-2xl font-black text-slate-900">{backends?.filter(b => b.is_enabled).length || 0} / {backends?.length || 0}</div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-xl"><Activity className="w-6 h-6" /></div>
          <div>
            <div className="text-slate-400 text-xs font-bold uppercase tracking-wider">Requisições Ativas</div>
            <div className="text-2xl font-black text-slate-900">142</div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-green-50 text-green-600 rounded-xl"><CheckCircle2 className="w-6 h-6" /></div>
          <div>
            <div className="text-slate-400 text-xs font-bold uppercase tracking-wider">Uptime Global</div>
            <div className="text-2xl font-black text-slate-900">99.98%</div>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="relative">
          <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
          <input 
            type="text" 
            placeholder="Buscar backends..."
            className="w-full pl-12 pr-4 py-3.5 bg-white border border-slate-200 rounded-2xl focus:ring-2 focus:ring-teal-500 outline-none shadow-sm transition-all"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {isLoading && (
            <div className="col-span-full py-20 text-center text-slate-400 font-medium">Carregando backends...</div>
          )}
          {filtered?.map(backend => (
            <div key={backend.id} className="bg-white border border-slate-200 rounded-2xl shadow-sm hover:shadow-md transition-all overflow-hidden group">
              <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${backend.is_enabled ? 'bg-teal-50 text-teal-600' : 'bg-slate-100 text-slate-400'}`}>
                      <Cpu className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-900 group-hover:text-teal-700 transition-colors">{backend.name}</h3>
                      <div className="text-xs font-mono text-slate-400">{backend.id}</div>
                    </div>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${
                    backend.is_enabled ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'
                  }`}>
                    {backend.is_enabled ? 'Online' : 'Offline'}
                  </span>
                </div>

                <div className="space-y-3 mb-6">
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <Terminal className="w-4 h-4 text-slate-400" />
                    <code className="bg-slate-50 px-2 py-0.5 rounded border border-slate-100 flex-1 truncate">{backend.base_url}</code>
                  </div>
                  <div className="flex items-center justify-between text-xs font-bold uppercase tracking-tight text-slate-400">
                    <span>Provider: {backend.provider_type}</span>
                    <span>Concurrency: {backend.max_concurrency}</span>
                  </div>
                </div>

                <div className="flex gap-2">
                  <button className="flex-1 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 text-sm font-bold rounded-xl transition-colors flex items-center justify-center gap-2">
                    <Info className="w-4 h-4" /> Detalhes
                  </button>
                  <button className="flex-1 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 text-sm font-bold rounded-xl transition-colors flex items-center justify-center gap-2">
                    <Activity className="w-4 h-4" /> Logs
                  </button>
                  <button className="px-3 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 rounded-xl transition-colors">
                    <AlertCircle className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="h-1 bg-slate-100 group-hover:bg-teal-500/20 transition-colors">
                <div className="h-full bg-teal-500 w-2/3"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
