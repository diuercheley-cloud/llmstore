import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/card'
import { Badge } from '../../components/badge'
import { Button } from '../../components/button'
import { Input } from '../../components/input'
import api from '../../lib/api'
import { 
  ShoppingBag, 
  ShieldCheck, 
  ShieldAlert, 
  Download, 
  ExternalLink,
  Info
} from 'lucide-react'
import { toast } from 'sonner'

export default function AgentMarketplace() {
  const [agents, setAgents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [dryRunResult, setDryRunResult] = useState<any>(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await (api as any).request('GET', '/api/admin/marketplace/agents')
      setAgents(res)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDryRun = async (packageUrl: string) => {
    try {
      const res = await (api as any).request('POST', '/api/admin/marketplace/install/dry-run', {
        data: { package_url: packageUrl }
      })
      setDryRunResult(res)
      toast.success("Dry-run concluído com sucesso.")
    } catch (err) {
      toast.error("Falha ao simular instalação.")
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Agent Marketplace</h1>
          <p className="text-muted-foreground">Instale agentes de terceiros com governança e segurança</p>
        </div>
        <Button variant="outline">
          <Download className="w-4 h-4 mr-2" /> Importar Localmente
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {agents.map((agent) => (
          <Card key={agent.id} className="overflow-hidden border-white/5 bg-slate-900/50 hover:border-blue-500/50 transition-all">
            <CardHeader className="pb-2">
              <div className="flex justify-between items-start">
                <CardTitle className="text-lg">{agent.name}</CardTitle>
                <Badge variant={agent.risk_level === 'low' ? 'secondary' : 'outline'}>
                  {agent.risk_level} risk
                </Badge>
              </div>
              <CardDescription>{agent.description}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-1">
                {agent.permissions.map((p: string) => (
                  <Badge key={p} variant="secondary" className="text-[10px] py-0">
                    {p}
                  </Badge>
                ))}
              </div>
              
              <div className="flex items-center gap-2 text-xs">
                {agent.attestation_status === 'verified' ? (
                  <div className="flex items-center text-emerald-400 gap-1">
                    <ShieldCheck size={14} /> Attestation Verified
                  </div>
                ) : (
                  <div className="flex items-center text-orange-400 gap-1">
                    <ShieldAlert size={14} /> Untrusted Source
                  </div>
                )}
              </div>

              <div className="pt-2 flex gap-2">
                <Button 
                  size="sm" 
                  className="flex-1" 
                  onClick={() => handleDryRun(`https://market.stack/packages/${agent.id}`)}
                >
                  Dry-run Install
                </Button>
                <Button size="sm" variant="ghost" className="px-2">
                  <ExternalLink size={14} />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}

        {agents.length === 0 && !loading && (
          <div className="col-span-full py-20 text-center border-2 border-dashed rounded-3xl border-white/5">
             <ShoppingBag className="w-12 h-12 mx-auto text-slate-700 mb-4" />
             <p className="text-muted-foreground">Nenhum agente disponível no marketplace.</p>
          </div>
        )}
      </div>

      {dryRunResult && (
        <Card className="border-blue-500/20 bg-blue-500/5">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Info className="text-blue-400 w-5 h-5" />
              <CardTitle className="text-lg">Resultado da Simulação de Instalação</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-bold mb-2 uppercase text-slate-500">Manifesto</h4>
                <pre className="text-xs p-3 bg-slate-950 rounded-lg overflow-auto max-h-40">
                  {JSON.stringify(dryRunResult.manifest, null, 2)}
                </pre>
              </div>
              <div>
                <h4 className="text-sm font-bold mb-2 uppercase text-slate-500">Avaliação de Política</h4>
                <div className="p-3 bg-slate-950 rounded-lg space-y-3">
                   <div className="flex justify-between items-center">
                     <span>Status:</span>
                     <Badge variant={dryRunResult.policy_evaluation === 'allowed' ? 'secondary' : 'destructive'}>
                       {dryRunResult.policy_evaluation}
                     </Badge>
                   </div>
                   {dryRunResult.warnings.map((w: string, i: number) => (
                     <div key={i} className="text-xs text-orange-400 flex items-start gap-2">
                       <ShieldAlert size={12} className="mt-0.5" /> {w}
                     </div>
                   ))}
                </div>
              </div>
            </div>
            <div className="flex justify-end pt-4">
              <Button onClick={() => setDryRunResult(null)} variant="ghost" className="mr-2">Cancelar</Button>
              <Button disabled={dryRunResult.policy_evaluation === 'blocked'}>Aprovar e Instalar</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
