import React, { useState } from 'react';
import FlowBuilder from './FlowBuilder';
import ToolPalette from './ToolPalette';
import MemoryConfigPanel from './MemoryConfigPanel';
import EvalConfigPanel from './EvalConfigPanel';
import DebuggerPanel from './DebuggerPanel';

export default function AgentStudio() {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    backgroundColor: '#0b0f19',
    color: '#f3f4f6',
    fontFamily: '"Outfit", "Inter", sans-serif',
    overflow: 'hidden',
  };

  const headerStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 24px',
    background: 'rgba(17, 24, 39, 0.7)',
    backdropFilter: 'blur(12px)',
    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
  };

  const titleStyle: React.CSSProperties = {
    fontSize: '20px',
    fontWeight: 'bold',
    background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    margin: 0,
  };

  const badgeStyle: React.CSSProperties = {
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
    border: '1px solid rgba(59, 130, 246, 0.3)',
    color: '#60a5fa',
    padding: '4px 10px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: 600,
  };

  const mainAreaStyle: React.CSSProperties = {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  };

  const sidebarStyle: React.CSSProperties = {
    width: '280px',
    background: 'rgba(15, 23, 42, 0.8)',
    borderRight: '1px solid rgba(255, 255, 255, 0.08)',
    display: 'flex',
    flexDirection: 'column',
    overflowY: 'auto',
  };

  const canvasAreaStyle: React.CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
  };

  const rightPanelStyle: React.CSSProperties = {
    width: '320px',
    background: 'rgba(15, 23, 42, 0.8)',
    borderLeft: '1px solid rgba(255, 255, 255, 0.08)',
    display: 'flex',
    flexDirection: 'column',
    overflowY: 'auto',
  };

  const buttonStyle: React.CSSProperties = {
    background: 'linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)',
    border: 'none',
    color: '#fff',
    padding: '8px 16px',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
    boxShadow: '0 4px 12px rgba(37, 99, 235, 0.2)',
    transition: 'transform 0.1s ease',
  };

  return (
    <div style={containerStyle}>
      <header style={headerStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h1 style={titleStyle}>Agent Studio</h1>
          <span style={badgeStyle}>Enterprise Engine v2.1</span>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button style={{ ...buttonStyle, background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}>Validate DAG</button>
          <button style={buttonStyle}>Deploy Flow</button>
        </div>
      </header>

      <div style={mainAreaStyle}>
        <aside style={sidebarStyle}>
          <ToolPalette />
        </aside>

        <main style={canvasAreaStyle}>
          <FlowBuilder onSelectNode={setSelectedNode} />
          <DebuggerPanel />
        </main>

        <aside style={rightPanelStyle}>
          <MemoryConfigPanel />
          <EvalConfigPanel />
        </aside>
      </div>
    </div>
  );
}
