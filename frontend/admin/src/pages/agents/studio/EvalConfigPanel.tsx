import React, { useState } from 'react';

export default function EvalConfigPanel() {
  const [suite, setSuite] = useState('baseline_smoke');
  const [autoOptimize, setAutoOptimize] = useState(false);

  const panelStyle: React.CSSProperties = {
    padding: '20px',
  };

  const headerStyle: React.CSSProperties = {
    fontSize: '14px',
    fontWeight: 600,
    marginBottom: '16px',
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
  };

  const selectStyle: React.CSSProperties = {
    width: '100%',
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '4px',
    color: '#fff',
    padding: '6px 10px',
    fontSize: '12px',
    marginBottom: '16px',
    boxSizing: 'border-box'
  };

  const rowStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: '13px'
  };

  return (
    <div style={panelStyle}>
      <h2 style={headerStyle}>Evaluation Suite</h2>
      <select value={suite} onChange={e => setSuite(e.target.value)} style={selectStyle}>
        <option value="baseline_smoke">Baseline Agent Smoke (10 cases)</option>
        <option value="jailbreak_resilience">Jailbreak & Guardrails (25 cases)</option>
        <option value="production_load">KG High Latency (5 cases)</option>
      </select>
      <div style={rowStyle}>
        <span>Prompt Auto-Optimizer</span>
        <input type="checkbox" checked={autoOptimize} onChange={e => setAutoOptimize(e.target.checked)} />
      </div>
    </div>
  );
}
