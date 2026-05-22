import React, { useState } from 'react';
import { Settings, Clock, ChevronDown, ChevronUp } from 'lucide-react';

interface ToolInvocationProps {
  toolName: string;
  latencyMs?: number;
  success: boolean;
  error?: string;
  inputHash?: string;
  outputSummary?: string;
}

export function ToolInvocationCard({ toolName, latencyMs, success, error, inputHash, outputSummary }: ToolInvocationProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`border rounded-xl p-4 ${success ? 'border-border bg-card' : 'border-destructive/30 bg-destructive/5'}`}>
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${success ? 'bg-primary/10 text-primary' : 'bg-destructive/10 text-destructive'}`}>
            <Settings className="w-4 h-4" />
          </div>
          <div>
            <h4 className="font-bold text-sm">{toolName}</h4>
            <div className="flex gap-3 text-[10px] text-muted-foreground font-mono mt-1">
               {latencyMs && <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {latencyMs}ms</span>}
               {inputHash && <span>Input Hash: {inputHash.slice(0, 8)}...</span>}
            </div>
          </div>
        </div>
        <button onClick={() => setExpanded(!expanded)} className="p-1 hover:bg-secondary rounded">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>
      
      {expanded && (
        <div className="mt-4 space-y-3">
          {error && (
            <div>
              <span className="text-[10px] font-black uppercase text-destructive tracking-widest">Error</span>
              <p className="text-xs text-destructive mt-1 font-mono">{error}</p>
            </div>
          )}
          {outputSummary && (
            <div>
              <span className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Output Summary</span>
              <p className="text-xs text-muted-foreground mt-1 bg-secondary/50 p-2 rounded">{outputSummary}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
