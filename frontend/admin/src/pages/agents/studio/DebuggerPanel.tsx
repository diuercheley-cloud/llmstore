import React, { useState } from 'react';

export default function DebuggerPanel() {
  const [logs, setLogs] = useState<string[]>([
    '[system] Debug session initialized.',
    '[reasoning] Plan: Retrieve documentation for Google owns Android context.',
    '[memory] Memory read: semantic_memory match (Google controls Android repository).',
    '[tool_call] Invoking code_interpreter inside secure mock sandbox...',
    '[tool_call] Code executed successfully. Exit code: 0.',
    '[system] Dry-run completed. All checks passed.'
  ]);

  const panelStyle: React.CSSProperties = {
    height: '240px',
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

  const handleDryRun = () => {
    setLogs(prev => [
      ...prev,
      `[user_action] Dry-run triggered at ${new Date().toLocaleTimeString()}`,
      '[reasoning_summary] Sanitized reasoning logic compiled: DAG validation success.'
    ]);
  };

  return (
    <div style={panelStyle}>
      <div style={headerStyle}>
        <span style={{ fontSize: '13px', fontWeight: 600, color: '#94a3b8' }}>Reasoning Console</span>
        <button
          onClick={handleDryRun}
          style={{
            background: '#10b981',
            border: 'none',
            color: '#fff',
            padding: '4px 12px',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: 'bold',
            cursor: 'pointer'
          }}
        >
          Run Diagnostic (Dry-run)
        </button>
      </div>
      <div style={consoleStyle}>
        {logs.map((log, i) => (
          <div key={i}>{log}</div>
        ))}
      </div>
    </div>
  );
}
