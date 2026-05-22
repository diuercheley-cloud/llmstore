import { useState } from 'react';
import { Settings, Activity, ChevronRight, Zap } from 'lucide-react';
import { AgentStatusBadge } from './AgentStatusBadge';

interface TimelineItem {
  id: string;
  timestamp: string;
  type: 'step' | 'event';
  step_number?: number;
  step_type?: string;
  status?: string;
  latency_ms?: number;
  error?: string;
  event_type?: string;
  payload?: any;
}

export function AgentRunTimelineComponent({ items }: { items: TimelineItem[] }) {
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});

  const toggleExpand = (id: string) => {
    setExpandedItems(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-6">
      {items.map((item, idx) => (
        <div key={item.id || idx} className="relative pl-8 before:absolute before:left-[11px] before:top-2 before:bottom-[-24px] before:w-[2px] before:bg-border last:before:hidden">
          <div className={`absolute left-0 top-1 w-6 h-6 rounded-full flex items-center justify-center border-2 border-background shadow-sm ${
            item.type === 'step' ? (
              item.status === 'success' ? 'bg-green-500 text-white' : 'bg-destructive text-white'
            ) : 'bg-primary text-white'
          }`}>
            {item.type === 'step' ? (
              item.step_type === 'tool_call' ? <Settings size={12} /> : 
              item.step_type === 'model_call' ? <Zap size={12} /> :
              <ChevronRight size={12} />
            ) : <Activity size={12} />}
          </div>
          
          <div>
            <div className="flex items-center gap-3 mb-1 cursor-pointer select-none" onClick={() => toggleExpand(item.id || String(idx))}>
              <h4 className="font-bold text-foreground text-sm hover:text-primary transition-colors">
                {item.type === 'step' ? `Step ${item.step_number}: ${item.step_type}` : `Event: ${item.event_type}`}
              </h4>
              <span className="text-[10px] font-mono text-muted-foreground">{new Date(item.timestamp).toLocaleTimeString()}</span>
              {item.status && <AgentStatusBadge status={item.status} />}
            </div>
            
            {item.type === 'step' && (
              <div className="text-xs text-muted-foreground flex gap-4">
                {item.latency_ms && <span>Latency: {item.latency_ms}ms</span>}
              </div>
            )}
            
            {item.error && (
              <div className="mt-2 p-3 bg-destructive/5 border border-destructive/10 rounded-xl text-destructive text-xs font-mono">
                {item.error}
              </div>
            )}
            
            {expandedItems[item.id || String(idx)] && item.payload && (
              <div className="mt-2">
                <div className="flex justify-between items-center bg-secondary/50 px-3 py-1.5 rounded-t-xl border border-border border-b-0">
                  <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Payload</span>
                </div>
                <pre className="p-3 bg-secondary/20 rounded-b-xl border border-border text-[10px] font-mono overflow-x-auto whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {/* Note: Sensitive data should be redacted at the API level or masked here based on RBAC */}
                  {JSON.stringify(item.payload, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      ))}
      
      {items.length === 0 && (
        <div className="text-center p-8 text-muted-foreground italic border border-dashed border-border rounded-xl">
          Nenhuma atividade registrada na timeline.
        </div>
      )}
    </div>
  );
}
