import React from 'react';
import { Network, ArrowRight } from 'lucide-react';

interface HandoffEvent {
  id: string;
  source_agent_id: string;
  target_agent_id: string;
  reason: string;
}

export function HandoffGraph({ events }: { events: HandoffEvent[] }) {
  if (!events || events.length === 0) {
    return (
      <div className="text-center p-8 border border-dashed border-border rounded-xl">
        <Network className="w-8 h-8 text-muted-foreground mx-auto mb-3 opacity-50" />
        <p className="text-muted-foreground text-sm font-medium">Nenhum handoff registrado nesta sessão.</p>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
      <h4 className="text-xs font-black uppercase tracking-widest text-muted-foreground mb-6">Cadeia de Delegação</h4>
      
      <div className="space-y-4">
        {events.map((event, idx) => (
          <div key={event.id} className="flex flex-col gap-2">
            <div className="flex items-center gap-4">
              <div className="flex-1 bg-secondary/50 p-3 rounded-xl border border-border">
                <span className="text-[10px] font-bold text-muted-foreground uppercase block mb-1">Origem</span>
                <span className="font-mono text-xs font-bold">{event.source_agent_id.slice(0, 8)}</span>
              </div>
              
              <div className="flex flex-col items-center justify-center w-24">
                <ArrowRight className="text-primary w-5 h-5 mb-1" />
                <span className="text-[9px] font-black uppercase text-primary tracking-tighter">Handoff</span>
              </div>
              
              <div className="flex-1 bg-primary/10 p-3 rounded-xl border border-primary/20">
                <span className="text-[10px] font-bold text-primary uppercase block mb-1">Destino</span>
                <span className="font-mono text-xs font-bold text-primary-foreground">{event.target_agent_id.slice(0, 8)}</span>
              </div>
            </div>
            
            <div className="px-4 py-2 bg-background border border-border rounded-lg text-xs italic text-muted-foreground flex items-start gap-2">
              <span className="font-bold not-italic">Motivo:</span> {event.reason}
            </div>
            
            {idx < events.length - 1 && (
              <div className="flex justify-center py-2">
                <div className="w-[2px] h-6 bg-border"></div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
