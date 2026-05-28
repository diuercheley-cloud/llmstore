import React, { useState } from 'react';

export default function MemoryConfigPanel() {
  const [episodic, setEpisodic] = useState(true);
  const [semantic, setSemantic] = useState(true);
  const [working, setWorking] = useState(true);
  const [retention, setRetention] = useState('30');

  const panelStyle: React.CSSProperties = {
    padding: '20px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
  };

  const headerStyle: React.CSSProperties = {
    fontSize: '14px',
    fontWeight: 600,
    marginBottom: '16px',
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
  };

  const rowStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
    fontSize: '13px'
  };

  const selectStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '4px',
    color: '#fff',
    padding: '4px 8px',
    fontSize: '12px'
  };

  return (
    <div style={panelStyle}>
      <h2 style={headerStyle}>Cognitive Memory</h2>
      <div style={rowStyle}>
        <span>Episodic Memory</span>
        <input type="checkbox" checked={episodic} onChange={e => setEpisodic(e.target.checked)} />
      </div>
      <div style={rowStyle}>
        <span>Semantic Memory</span>
        <input type="checkbox" checked={semantic} onChange={e => setSemantic(e.target.checked)} />
      </div>
      <div style={rowStyle}>
        <span>Working Memory</span>
        <input type="checkbox" checked={working} onChange={e => setWorking(e.target.checked)} />
      </div>
      <div style={rowStyle}>
        <span>Retention Window</span>
        <select value={retention} onChange={e => setRetention(e.target.value)} style={selectStyle}>
          <option value="7">7 Days</option>
          <option value="30">30 Days</option>
          <option value="90">90 Days</option>
          <option value="never">Infinite</option>
        </select>
      </div>
    </div>
  );
}
