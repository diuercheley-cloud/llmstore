import { Database, Network, Share2, GitBranch } from 'lucide-react'

export default function KnowledgeGraph() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-10">
        <h1 className="text-4xl font-black text-foreground tracking-tight">Knowledge <span className="text-primary">Graph</span></h1>
        <p className="text-muted-foreground font-medium text-lg">Gestão de entidades, relações e memória semântica para agentes.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <div className="lg:col-span-3 h-[600px] bg-card border border-border rounded-3xl relative overflow-hidden flex items-center justify-center border-dashed">
          <div className="text-center">
             <Network className="w-16 h-16 text-muted-foreground/20 mx-auto mb-4" />
             <h2 className="text-xl font-bold text-muted-foreground">Visualizador de Grafo em desenvolvimento</h2>
             <p className="text-sm text-muted-foreground max-w-sm mx-auto mt-2">
               Estamos integrando o motor de visualização para suportar milhões de triplas RDF em tempo real.
             </p>
          </div>
          
          {/* Mock floating nodes */}
          <div className="absolute top-20 left-40 p-4 bg-background border border-primary/20 rounded-2xl shadow-xl animate-bounce" style={{ animationDuration: '4s' }}>
            <div className="text-[10px] font-black uppercase text-primary">Entity</div>
            <div className="font-bold">User: 12345</div>
          </div>
          <div className="absolute bottom-40 right-40 p-4 bg-background border border-amber-200 rounded-2xl shadow-xl animate-pulse">
            <div className="text-[10px] font-black uppercase text-amber-600">Product</div>
            <div className="font-bold">LLM-Stack-Pro</div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-card border border-border rounded-3xl p-6">
            <h3 className="text-xs font-black text-muted-foreground uppercase tracking-widest mb-4">Estatísticas</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Entidades</span>
                <span className="font-bold">12,450</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Relações</span>
                <span className="font-bold">45,821</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Memory Loopback</span>
                <span className="text-emerald-500 text-[10px] font-black uppercase">Active</span>
              </div>
            </div>
          </div>

          <div className="bg-foreground text-background rounded-3xl p-6">
             <h3 className="text-xs font-black uppercase tracking-widest mb-4 flex items-center gap-2">
               <Database className="w-4 h-4" />
               Storage Engine
             </h3>
             <div className="space-y-3">
               <div className="p-3 bg-background/10 rounded-xl border border-border/20">
                  <div className="text-[10px] font-black uppercase text-muted-foreground">Type</div>
                  <div className="text-sm font-bold">Neo4j / FalkorDB</div>
               </div>
               <div className="p-3 bg-background/10 rounded-xl border border-border/20">
                  <div className="text-[10px] font-black uppercase text-muted-foreground">Sync Latency</div>
                  <div className="text-sm font-bold">12ms (avg)</div>
               </div>
             </div>
          </div>
        </div>
      </div>
    </div>
  )
}
