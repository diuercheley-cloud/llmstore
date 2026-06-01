import React, { useMemo } from 'react';
import { useAgentRunStream } from '../../../hooks/useAgentRunStream';
import type { StreamEvent } from '../../../hooks/useAgentRunStream';
import { Terminal, Wifi, WifiOff, XCircle, Play, Pause } from 'lucide-react';

interface DebuggerPanelProps {
  runId?: string;
}

export default function DebuggerPanel({ runId }: DebuggerPanelProps) {
  const { status, events, error, sendCommand } = useAgentRunStream(runId);

  const getStatusColor = (s: string) => {
    switch (s) {
      case 'connected': return 'text-emerald-400';
      case 'connecting': return 'text-amber-400';
      case 'reconnecting': return 'text-orange-400';
      case 'idle': return 'text-slate-500';
      case 'failed':
      default: return 'text-red-400';
    }
  };

  // Convert raw WebSocket events to formatted lines
  const formattedLogs = useMemo(() => {
    const lines: string[] = [];
    let modelText = '';

    const formatEvent = (evt: StreamEvent): string => {
      const time = new Date(evt.timestamp).toLocaleTimeString();
      const prefix = `[${time}]`;

      switch (evt.event) {
        case 'run.started': return `${prefix} [system] Run started.`;
        case 'step.started': return `${prefix} [system] Executing step...`;
        case 'model.delta': return `${prefix} [reasoning] ${evt.data?.chunk || ''}`;
        case 'tool.called': return `${prefix} [tool_call] Invoking ${evt.data?.tool_name} with parameters: ${JSON.stringify(evt.data?.parameters)}`;
        case 'tool.completed': return `${prefix} [tool_call] Tool ${evt.data?.tool_name} completed. Output: ${JSON.stringify(evt.data?.output)}`;
        case 'approval.required': return `${prefix} [approval] Human approval required for tool: ${evt.data?.tool_name}`;
        case 'memory.read': return `${prefix} [memory] Memory read from key: ${evt.data?.key}`;
        case 'policy.denied': return `${prefix} [policy] Policy denied execution: ${evt.data?.reason}`;
        case 'run.completed': return `${prefix} [system] Run completed successfully.`;
        case 'run.failed': return `${prefix} [system] Run failed: ${evt.data?.error || 'Unknown error'}`;
        default: return `${prefix} [${evt.event}] ${JSON.stringify(evt.data)}`;
      }
    };

    events.forEach((evt) => {
      if (evt.event === 'model.delta') {
        modelText += evt.data?.chunk || '';
      } else {
        if (modelText) {
          const time = new Date(evt.timestamp).toLocaleTimeString();
          lines.push(`[${time}] [reasoning] ${modelText}`);
          modelText = '';
        }
        lines.push(formatEvent(evt));
      }
    });

    if (modelText) {
      const time = new Date().toLocaleTimeString();
      lines.push(`[${time}] [reasoning] ${modelText}`);
    }

    return lines;
  }, [events]);

  return (
    <div className="flex flex-col h-full bg-[#050811] text-slate-300 font-mono text-[11px]">
      <div className="flex items-center justify-between px-4 h-10 border-b border-white/5 bg-white/[0.02]">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-slate-500 font-black uppercase tracking-widest text-[10px]">
            <Terminal size={12} />
            Reasoning Console
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full ${status === 'connected' ? 'bg-emerald-500 animate-pulse' : 'bg-slate-700'}`} />
            <span className={`text-[10px] font-bold uppercase tracking-wider ${getStatusColor(status)}`}>
              {status}
            </span>
          </div>
        </div>

        {runId && status === 'connected' && (
          <div className="flex items-center gap-2">
            <button onClick={() => sendCommand('pause')} className="p-1 hover:bg-white/5 rounded text-slate-500 hover:text-white transition-colors" title="Pause">
              <Pause size={14} />
            </button>
            <button onClick={() => sendCommand('resume')} className="p-1 hover:bg-white/5 rounded text-slate-500 hover:text-white transition-colors" title="Resume">
              <Play size={14} />
            </button>
            <button onClick={() => sendCommand('cancel')} className="flex items-center gap-1.5 px-2 py-0.5 bg-red-500/10 hover:bg-red-500/20 text-red-500 rounded text-[10px] font-bold transition-colors ml-2">
              <XCircle size={10} />
              Abort
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-1 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
        {error && (
          <div className="flex items-center gap-2 text-red-400 bg-red-500/5 p-2 rounded-lg border border-red-500/10 mb-4">
            <WifiOff size={14} />
            <span>Connection Error: {error}</span>
          </div>
        )}

        {!runId ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-700 gap-2 opacity-40">
            <Wifi size={24} strokeWidth={1} />
            <p>No active session. Deploy a flow to start debugging.</p>
          </div>
        ) : formattedLogs.length === 0 ? (
          <div className="flex items-center gap-2 text-slate-600 animate-pulse">
            <span className="w-1 h-3 bg-blue-500" />
            Awaiting streaming events from runtime...
          </div>
        ) : (
          formattedLogs.map((log, i) => (
            <div key={i} className="whitespace-pre-wrap leading-relaxed hover:bg-white/[0.02] px-1 rounded transition-colors">
              <span className="text-slate-600 font-bold">{log.slice(0, 10)}</span>
              <span className={log.includes('[reasoning]') ? 'text-blue-400' : 
                              log.includes('[tool_call]') ? 'text-purple-400' : 
                              log.includes('[system]') ? 'text-emerald-400' : 
                              log.includes('[policy]') ? 'text-red-400' : 'text-slate-300'}>
                {log.slice(10)}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

