import { Tag, Rocket, History, Download } from 'lucide-react'
import HealthCard from '../../components/operations/HealthCard'

export default function ReleaseStatus() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-black text-foreground mb-8">Release <span className="text-primary">Status</span></h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
        <HealthCard 
          title="Versão Atual" 
          value="v1.2.0-stable" 
          icon={<Tag className="w-6 h-6" />}
          description="Build hash: 7f2d9a1 (2024-05-18)"
        />
        <HealthCard 
          title="Status do Deploy" 
          value="COMPLETE" 
          icon={<Rocket className="w-6 h-6" />}
          description="Propagação em 100% dos clusters."
        />
      </div>

      <div className="bg-card border border-border rounded-3xl p-8 shadow-sm">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-bold text-foreground flex items-center gap-2">
            <History className="w-6 h-6 text-primary" />
            Histórico de Mudanças
          </h3>
          <button className="text-primary font-bold text-sm flex items-center gap-1">
            <Download className="w-4 h-4" />
            Release Summary
          </button>
        </div>

        <div className="prose prose-slate max-w-none">
          <div className="p-6 bg-secondary rounded-2xl border border-border">
             <h4 className="text-foreground font-bold mb-4">v1.2.0 - "Antigravity" Update</h4>
             <ul className="space-y-2 text-muted-foreground text-sm list-disc pl-5">
               <li>Implementação da nova camada de UX Operacional (Admin v2)</li>
               <li>Suporte a Hot-Swap em provedores llama.cpp</li>
               <li>Novas métricas de QoS e faturamento de prioridade</li>
               <li>Melhoria de 15% na latência de roteamento entre clusters</li>
               <li>Correção de vazamento de memória em streams longos</li>
             </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
