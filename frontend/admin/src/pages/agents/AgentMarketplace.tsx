import React from 'react';
import { Package, Download, Star, ExternalLink } from 'lucide-react';
import { AgentStatusBadge } from '../../components/agents/AgentStatusBadge';

export default function AgentMarketplace() {
  const bundles = [
    { id: "1", name: "support-triage-agent", category: "support", author: "Platform Team", rating: 4.8, official: true, installed: true },
    { id: "2", name: "compliance-evidence-agent", category: "security", author: "Platform Team", rating: 4.9, official: true, installed: false },
    { id: "3", name: "ops-readiness-agent", category: "operations", author: "Community", rating: 4.2, official: false, installed: false },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black tracking-tight">Agent <span className="text-primary">Marketplace</span></h1>
          <p className="text-muted-foreground mt-2 text-lg">Descubra e instale templates de agentes assinados e validados.</p>
        </div>
        <button className="bg-primary text-primary-foreground px-4 py-2.5 rounded-xl font-bold flex items-center gap-2 hover:opacity-90 transition-opacity">
          <Download size={18} /> Instalar Bundle (Local)
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {bundles.map(bundle => (
          <div key={bundle.id} className="bg-card border border-border rounded-3xl p-6 shadow-sm hover:border-primary/50 transition-colors flex flex-col h-full">
            <div className="flex justify-between items-start mb-4">
              <div className="p-3 bg-primary/10 text-primary rounded-xl">
                <Package className="w-6 h-6" />
              </div>
              {bundle.official && (
                <span className="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded bg-blue-500/10 text-blue-600 border border-blue-500/20">
                  Official
                </span>
              )}
            </div>
            
            <h3 className="font-bold text-foreground text-lg">{bundle.name}</h3>
            <p className="text-sm text-muted-foreground mt-1">por {bundle.author}</p>
            
            <div className="flex items-center gap-4 mt-4">
               <div className="flex items-center gap-1 text-sm font-bold text-yellow-500">
                 <Star className="w-4 h-4 fill-current" /> {bundle.rating}
               </div>
               <span className="text-xs font-mono text-muted-foreground bg-secondary/50 px-2 py-0.5 rounded">{bundle.category}</span>
            </div>
            
            <div className="mt-auto pt-6 flex gap-3">
              {bundle.installed ? (
                <button className="flex-1 bg-secondary text-foreground font-bold py-2 rounded-xl text-sm" disabled>Instalado</button>
              ) : (
                <button className="flex-1 bg-foreground text-background font-bold py-2 rounded-xl hover:opacity-90 text-sm">Instalar</button>
              )}
              <button className="p-2 border border-border rounded-xl text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors">
                <ExternalLink size={18} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
