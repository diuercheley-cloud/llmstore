import React, { useMemo } from 'react';
import { useAgentRunStream } from '../../../hooks/useAgentRunStream';
import type { StreamEvent } from '../../../hooks/useAgentRunStream';

interface DebuggerPanelProps {
  runId?: string;
}

export default function DebuggerPanel({ runId }: DebuggerPanelProps) {
  const { status, events, error, sendCommand } = useAgentRunStream(runId);

  const panelStyle: React.CSSProperties = {
    height: '280px',
    background: 'rgba(9, 15, 28, 0.95)',
    borderTop: '1px solid rgba(255, 255, 255, 0.08)',
    display: 'flex',
    flexDirection: 'column',
  };

  const headerStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 16px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
  };

  const consoleStyle: React.CSSProperties = {
    flex: 1,
    padding: '16px',
    fontFamily: '"Courier New", Courier, monospace',
    fontSize: '12px',
    overflowY: 'auto',
    color: '#34d399',
    lineHeight: '1.6',
  };

  const getStatusColor = (s: string) => {
    switch (s) {
      case 'connected':
        return '#10b981'; // Green
      case 'connecting':
        return '#eab308'; // Yellow
      case 'reconnecting':
        return '#f97316'; // Orange
      case 'failed':
      default:
        return '#ef4444'; // Red
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
        case 'run.started':
          return `${prefix} [system] Run started.`;
        case 'step.started':
          return `${prefix} [system] Executing step...`;
        case 'model.delta':
          return `${prefix} [reasoning] ${evt.data?.chunk || ''}`;
        case 'tool.called':
          return `${prefix} [tool_call] Invoking ${evt.data?.tool_name} with parameters: ${JSON.stringify(evt.data?.parameters)}`;
        case 'tool.completed':
          return `${prefix} [tool_call] Tool ${evt.data?.tool_name} completed. Output: ${JSON.stringify(evt.data?.output)}`;
        case 'approval.required':
          return `${prefix} [approval] Human approval required for tool: ${evt.data?.tool_name}`;
        case 'memory.read':
          return `${prefix} [memory] Memory read from key: ${evt.data?.key}`;
        case 'policy.denied':
          return `${prefix} [policy] Policy denied execution: ${evt.data?.reason}`;
        case 'run.completed':
          return `${prefix} [system] Run completed successfully.`;
        case 'run.failed':
          return `${prefix} [system] Run failed: ${evt.data?.error || 'Unknown error'}`;
        default:
          return `${prefix} [${evt.event}] ${JSON.stringify(evt.data)}`;
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

  if (!runId) {
    return (
      <div style={panelStyle} id="debugger-panel-empty">
        <div style={headerStyle}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: '#94a3b8' }}>Reasoning Console</span>
        </div>
        <div style={{ ...consoleStyle, color: '#94a3b8', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          No active debug run. Select or start a run to stream debugger output.
        </div>
      </div>
    );
  }

  return (
    <div style={panelStyle} id="debugger-panel-active">
      <div style={headerStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: '#94a3b8' }}>Reasoning Console</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: getStatusColor(status),
                display: 'inline-block',
              }}
            />
            <span style={{ fontSize: '11px', fontWeight: 500, color: '#64748b', textTransform: 'capitalize' }}>
              {status}
            </span>
          </div>
        </div>
        {status === 'connected' && (
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => sendCommand('pause')}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                color: '#fff',
                padding: '4px 10px',
                borderRadius: '4px',
                fontSize: '11px',
                cursor: 'pointer',
              }}
            >
              Pause
            </button>
            <button
              onClick={() => sendCommand('resume')}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                color: '#fff',
                padding: '4px 10px',
                borderRadius: '4px',
                fontSize: '11px',
                cursor: 'pointer',
              }}
            >
              Resume
            </button>
            <button
              onClick={() => sendCommand('cancel')}
              style={{
                background: '#ef4444',
                border: 'none',
                color: '#fff',
                padding: '4px 10px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 'bold',
                cursor: 'pointer',
              }}
            >
              Cancel Run
            </button>
          </div>
        )}
      </div>

      {error && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.15)',
            borderBottom: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#ef4444',
            padding: '6px 16px',
            fontSize: '11px',
            fontWeight: 500,
          }}
          id="debugger-panel-warning"
        >
          Warning: WebSocket connection error - {error}
        </div>
      )}

      <div style={consoleStyle} id="debugger-console-logs">
        {formattedLogs.length === 0 ? (
          <div style={{ color: '#64748b', fontStyle: 'italic' }}>Awaiting events...</div>
        ) : (
          formattedLogs.map((log, i) => (
            <div key={i} style={{ whiteSpace: 'pre-wrap' }}>
              {log}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
