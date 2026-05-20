import { ShieldCheck, Lock, Eye, Download, AlertTriangle } from 'lucide-react'
import HealthCard from '../../components/operations/HealthCard'

export default function SecurityPosture() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-black text-foreground mb-2">Security <span className="text-primary">Posture</span></h1>
          <p className="text-muted-foreground font-medium">Monitoramento de conformidade, criptografia e auditoria.</p>
        </div>
        <button className="bg-primary text-white px-4 py-2 rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-primary/20">
          <Download className="w-4 h-4" />
          Baixar Relatório
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <HealthCard 
          title="Criptografia" 
          value="ATIVA" 
          icon={<Lock className="w-6 h-6" />}
          description="Tenant-level keys estão rotacionadas."
        />
        <HealthCard 
          title="Auditoria" 
          value="99.9%" 
          icon={<Eye className="w-6 h-6" />}
          description="Ações administrativas logadas e assinadas."
        />
        <HealthCard 
          title="Vulnerabilidades" 
          value="0" 
          icon={<ShieldCheck className="w-6 h-6" />}
          description="Nenhum CVE crítico detectado nos nós."
        />
      </div>

      <div className="bg-card border border-border rounded-3xl p-8 shadow-sm">
        <h3 className="text-xl font-bold text-foreground mb-6">Últimos Eventos de Segurança</h3>
        <div className="space-y-4">
          {[
            { event: 'Rotação de Master Key', status: 'success', time: '2h atrás' },
            { event: 'Tentativa de acesso não autorizado (Node-05)', status: 'warning', time: '5h atrás' },
            { event: 'Novo certificado PKI emitido', status: 'success', time: '12h atrás' },
          ].map((e, i) => (
            <div key={i} className="flex items-center justify-between p-4 bg-secondary rounded-2xl">
              <div className="flex items-center gap-3">
                {e.status === 'success' ? (
                  <ShieldCheck className="w-5 h-5 text-primary" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-yellow-500" />
                )}
                <span className="font-bold text-foreground">{e.event}</span>
              </div>
              <span className="text-xs text-muted-foreground font-mono">{e.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
