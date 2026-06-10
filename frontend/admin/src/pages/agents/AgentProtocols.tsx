import { useQuery, useMutation } from '@tanstack/react-query'
import api from '../../lib/api'
import { Server, Users, ShieldCheck, Activity, Terminal, Play, CheckCircle2, AlertCircle, Info } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

export default function AgentProtocols() {
  const [activeTab, setActiveTab] = useState('mcp-servers')
  const [handshakeResult, setHandshakeResult] = useState<any>(null)

  const { data: mcpServers, isLoading: isLoadingMcp } = useQuery({
    queryKey: ['mcp-servers'],
    queryFn: async () => {
      const res = await api.get('/admin/agents/protocols/mcp/servers')
      return res.data
    }
  })

  const handshakeMutation = useMutation({
    mutationFn: async (url: string) => {
      const res = await api.post(`/admin/agents/protocols/a2a/handshake/dry-run?peer_url=${encodeURIComponent(url)}`)
      return res.data
    },
    onSuccess: (data) => {
      setHandshakeResult(data)
      toast.success('Handshake simulado com sucesso')
    }
  })

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-3xl font-black text-foreground flex items-center gap-3">
          <ShieldCheck className="w-8 h-8 text-primary" /> AGENT PROTOCOLS
        </h1>
        <p className="text-muted-foreground mt-1">Gestão de MCP (Model Context Protocol), A2A (Agent-to-Agent) e camadas de confiança.</p>
      </div>

      <div className="bg-card border border-border rounded-3xl overflow-hidden">
        <div className="flex border-b border-border bg-secondary/20">
          <button 
            onClick={() => setActiveTab('mcp-servers')}
            className={`px-6 py-4 text-sm font-bold border-b-2 transition-all ${activeTab === 'mcp-servers' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground'}`}
          >
            MCP Servers
          </button>
          <button 
            onClick={() => setActiveTab('a2a-peers')}
            className={`px-6 py-4 text-sm font-bold border-b-2 transition-all ${activeTab === 'a2a-peers' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground'}`}
          >
            A2A Peers
          </button>
          <button 
            onClick={() => setActiveTab('trust-policies')}
            className={`px-6 py-4 text-sm font-bold border-b-2 transition-all ${activeTab === 'trust-policies' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground'}`}
          >
            Trust Policies
          </button>
        </div>

        <div className="p-6">
          {activeTab === 'mcp-servers' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {mcpServers?.map((s: any) => (
                  <div key={s.id} className="p-4 bg-secondary/30 border border-border rounded-2xl space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="font-black text-sm uppercase">{s.name}</span>
                      <span className="text-[10px] px-2 py-0.5 bg-primary/10 text-primary rounded-full font-bold uppercase">{s.trust_level}</span>
                    </div>
                    <div className="text-[10px] font-mono text-muted-foreground truncate">{s.endpoint}</div>
                    <div className="flex gap-2">
                      <button className="text-[10px] font-black uppercase text-primary hover:underline">Discover Tools</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'a2a-peers' && (
            <div className="space-y-6">
              <div className="bg-primary/5 border border-primary/10 rounded-2xl p-6">
                <h3 className="font-bold mb-4 flex items-center gap-2">
                  <Play className="w-4 h-4 text-primary" /> Testar Handshake (Dry-Run)
                </h3>
                <div className="flex gap-4">
                  <input 
                    id="peer-url"
                    type="text" 
                    placeholder="https://remote-agent.internal/a2a"
                    className="flex-1 bg-background border border-border rounded-xl px-4 py-2 text-sm"
                  />
                  <button 
                    onClick={() => handshakeMutation.mutate((document.getElementById('peer-url') as HTMLInputElement).value)}
                    className="px-6 py-2 bg-primary text-primary-foreground rounded-xl font-black text-sm"
                  >
                    EXECUTAR
                  </button>
                </div>
                {handshakeResult && (
                  <div className="mt-4 p-4 bg-background border border-border rounded-xl font-mono text-[10px] whitespace-pre-wrap">
                    {JSON.stringify(handshakeResult, null, 2)}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'trust-policies' && (
            <div className="space-y-4">
              <div className="p-4 border border-border rounded-2xl flex justify-between items-center">
                <div>
                  <div className="font-bold text-sm">Require Approval for Remote Tools</div>
                  <div className="text-xs text-muted-foreground">Always prompt admin for non-internal MCP servers.</div>
                </div>
                <div className="w-10 h-5 bg-primary rounded-full" />
              </div>
              <div className="p-4 border border-border rounded-2xl flex justify-between items-center">
                <div>
                  <div className="font-bold text-sm">Force Message Signing</div>
                  <div className="text-xs text-muted-foreground">Require Ed25519 signatures for A2A communication.</div>
                </div>
                <div className="w-10 h-5 bg-secondary rounded-full" />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
