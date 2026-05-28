import React, { useState } from 'react';

export default function ToolPalette() {
  const [search, setSearch] = useState('');
  const tools = [
    { name: 'code_interpreter', risk: 'medium', desc: 'Secure local python runner' },
    { name: 'vector_search', risk: 'low', desc: 'Search documentation' },
    { name: 'database_delete', risk: 'critical', desc: 'Destructive DB operations' },
    { name: 'shell_execution', risk: 'high', desc: 'Run OS commands' },
    { name: 'mcp_echo', risk: 'low', desc: 'MCP safe echo service' }
  ];

  const paletteStyle: React.CSSProperties = {
    padding: '20px',
  };

  const headerStyle: React.CSSProperties = {
    fontSize: '16px',
    fontWeight: 600,
    marginBottom: '16px',
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
  };

  const searchStyle: React.CSSProperties = {
    width: '100%',
    padding: '8px 12px',
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '6px',
    color: '#fff',
    fontSize: '13px',
    marginBottom: '16px',
    boxSizing: 'border-box'
  };

  const toolCardStyle: React.CSSProperties = {
    background: 'rgba(255, 255, 255, 0.02)',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    padding: '12px',
    borderRadius: '6px',
    marginBottom: '12px',
    cursor: 'grab',
  };

  const riskBadge = (risk: string): React.CSSProperties => {
    let color = '#10b981';
    let bg = 'rgba(16, 185, 129, 0.1)';
    if (risk === 'high') {
      color = '#ef4444';
      bg = 'rgba(239, 68, 68, 0.1)';
    } else if (risk === 'medium') {
      color = '#f59e0b';
      bg = 'rgba(245, 158, 11, 0.1)';
    } else if (risk === 'critical') {
      color = '#dc2626';
      bg = 'rgba(220, 38, 38, 0.2)';
    }

    return {
      fontSize: '9px',
      fontWeight: 'bold',
      color,
      backgroundColor: bg,
      padding: '2px 6px',
      borderRadius: '4px',
      textTransform: 'uppercase'
    };
  };

  const filteredTools = tools.filter(t => t.name.includes(search.toLowerCase()));

  return (
    <div style={paletteStyle}>
      <h2 style={headerStyle}>Tool Palette</h2>
      <input
        type="text"
        placeholder="Search tools..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        style={searchStyle}
      />
      <div>
        {filteredTools.map(t => (
          <div key={t.name} style={toolCardStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>{t.name}</span>
              <span style={riskBadge(t.risk)}>{t.risk}</span>
            </div>
            <p style={{ margin: 0, fontSize: '11px', color: 'rgba(255,255,255,0.4)' }}>{t.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
