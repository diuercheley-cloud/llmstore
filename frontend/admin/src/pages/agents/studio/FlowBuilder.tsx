import React, { useState } from 'react';

interface FlowNode {
  id: string;
  type: string;
  label: string;
  status: 'idle' | 'success' | 'running' | 'failed';
  config: string;
}

interface FlowBuilderProps {
  onSelectNode: (id: string | null) => void;
}

export default function FlowBuilder({ onSelectNode }: FlowBuilderProps) {
  const [nodes, setNodes] = useState<FlowNode[]>([
    { id: '1', type: 'llm_call', label: 'Reasoning Loop (LLM)', status: 'success', config: 'Model: Gemini-1.5-Pro' },
    { id: '2', type: 'tool_call', label: 'Code Sandbox Run', status: 'running', config: 'Provider: Docker (mock)' },
    { id: '3', type: 'approval', label: 'Human Review Check', status: 'idle', config: 'Role: Admin Write' },
    { id: '4', type: 'final', label: 'Publish Artifacts', status: 'idle', config: 'Formats: JSON, MD' },
  ]);

  const [activeNode, setActiveNode] = useState<string | null>(null);

  const containerStyle: React.CSSProperties = {
    flex: 1,
    padding: '24px',
    background: 'radial-gradient(circle, rgba(15,23,42,1) 0%, rgba(9,15,28,1) 100%)',
    position: 'relative',
    overflow: 'auto',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
  };

  const flowRowStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '40px',
    zIndex: 2,
  };

  const cardStyle = (node: FlowNode): React.CSSProperties => {
    const isActive = activeNode === node.id;
    let borderColor = 'rgba(255, 255, 255, 0.08)';
    let glowColor = 'transparent';

    if (isActive) {
      borderColor = '#3b82f6';
      glowColor = 'rgba(59, 130, 246, 0.2)';
    } else if (node.status === 'running') {
      borderColor = '#f59e0b';
      glowColor = 'rgba(245, 158, 11, 0.2)';
    } else if (node.status === 'success') {
      borderColor = '#10b981';
      glowColor = 'rgba(16, 185, 129, 0.1)';
    }

    return {
      width: '200px',
      background: 'rgba(17, 24, 39, 0.75)',
      borderRadius: '8px',
      padding: '16px',
      border: `1px solid ${borderColor}`,
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      boxShadow: `0 4px 20px ${glowColor}`,
    };
  };

  const typeBadgeStyle = (type: string): React.CSSProperties => {
    let color = '#3b82f6';
    let bg = 'rgba(59, 130, 246, 0.1)';
    if (type === 'tool_call') {
      color = '#a855f7';
      bg = 'rgba(168, 85, 247, 0.1)';
    } else if (type === 'approval') {
      color = '#f59e0b';
      bg = 'rgba(245, 158, 11, 0.1)';
    } else if (type === 'final') {
      color = '#10b981';
      bg = 'rgba(16, 185, 129, 0.1)';
    }

    return {
      fontSize: '10px',
      textTransform: 'uppercase',
      fontWeight: 'bold',
      color,
      backgroundColor: bg,
      padding: '2px 6px',
      borderRadius: '4px',
      display: 'inline-block',
      marginBottom: '8px',
    };
  };

  const arrowStyle: React.CSSProperties = {
    color: 'rgba(255, 255, 255, 0.2)',
    fontSize: '24px',
    fontWeight: 'bold',
    userSelect: 'none',
  };

  const handleCardClick = (id: string) => {
    setActiveNode(id);
    onSelectNode(id);
  };

  return (
    <div style={containerStyle}>
      <div style={{ position: 'absolute', top: 16, left: 16, fontSize: '14px', color: 'rgba(255,255,255,0.4)' }}>
        Interactive Dag Canvas
      </div>
      <div style={flowRowStyle}>
        {nodes.map((node, index) => (
          <React.Fragment key={node.id}>
            <div style={cardStyle(node)} onClick={() => handleCardClick(node.id)}>
              <span style={typeBadgeStyle(node.type)}>{node.type.replace('_', ' ')}</span>
              <h3 style={{ margin: '0 0 6px 0', fontSize: '14px', fontWeight: 600 }}>{node.label}</h3>
              <p style={{ margin: 0, fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>{node.config}</p>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '12px', fontSize: '11px' }}>
                <span style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: node.status === 'success' ? '#10b981' : node.status === 'running' ? '#f59e0b' : 'rgba(255,255,255,0.2)',
                  display: 'inline-block'
                }}></span>
                <span style={{ textTransform: 'capitalize', color: 'rgba(255,255,255,0.7)' }}>{node.status}</span>
              </div>
            </div>
            {index < nodes.length - 1 && <div style={arrowStyle}>→</div>}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
