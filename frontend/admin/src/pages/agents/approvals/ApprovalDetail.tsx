import React, { useState } from 'react';

interface ApprovalRequest {
  id: string;
  agent_run_id: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  reason: string;
  requested_by: string;
  status: string;
  expires_at: string;
  tenant_id: string;
  agent_name: string;
}

interface ApprovalDetailProps {
  request: ApprovalRequest;
  onDecision: (id: string, decision: string) => void;
}

export default function ApprovalDetail({ request, onDecision }: ApprovalDetailProps) {
  const [comment, setComment] = useState('');

  const detailStyle: React.CSSProperties = {
    padding: '32px',
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    boxSizing: 'border-box'
  };

  const titleStyle: React.CSSProperties = {
    fontSize: '18px',
    fontWeight: 'bold',
    marginBottom: '20px',
    color: '#f3f4f6'
  };

  const labelStyle: React.CSSProperties = {
    fontSize: '11px',
    color: '#94a3b8',
    textTransform: 'uppercase',
    fontWeight: 600,
    marginBottom: '4px'
  };

  const valueStyle: React.CSSProperties = {
    fontSize: '13px',
    color: '#e2e8f0',
    marginBottom: '16px'
  };

  const contextBoxStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.02)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: '6px',
    padding: '12px',
    fontFamily: '"Courier New", Courier, monospace',
    fontSize: '11px',
    color: '#f43f5e',
    marginBottom: '24px',
    whiteSpace: 'pre-wrap'
  };

  const textareaStyle: React.CSSProperties = {
    width: '100%',
    height: '80px',
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '6px',
    color: '#fff',
    padding: '8px 12px',
    fontSize: '13px',
    marginBottom: '20px',
    boxSizing: 'border-box'
  };

  const buttonStyle = (bg: string): React.CSSProperties => ({
    flex: 1,
    background: bg,
    border: 'none',
    color: '#fff',
    padding: '10px 16px',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '13px',
    textAlign: 'center'
  });

  return (
    <div style={detailStyle}>
      <h2 style={titleStyle}>Review Request: {request.id}</h2>

      <div style={labelStyle}>Agent Name</div>
      <div style={valueStyle}>{request.agent_name}</div>

      <div style={labelStyle}>Requested Action</div>
      <div style={valueStyle}>{request.reason}</div>

      <div style={labelStyle}>Risk Classification</div>
      <div style={{ ...valueStyle, textTransform: 'capitalize', fontWeight: 'bold' }}>{request.risk_level}</div>

      <div style={labelStyle}>Sanitized Execution Context</div>
      <div style={contextBoxStyle}>
        {`{
  "target_action": "DATABASE_MUTATION",
  "statement": "DELETE FROM customer_pricing WHERE id = [REDACTED]",
  "impact": "high_revenue_risk",
  "audit": "recorded"
}`}
      </div>

      <div style={labelStyle}>Reviewer Comment (optional)</div>
      <textarea
        placeholder="Add rationale for approval/rejection..."
        value={comment}
        onChange={e => setComment(e.target.value)}
        style={textareaStyle}
      />

      <div style={{ display: 'flex', gap: '12px', marginTop: 'auto' }}>
        <button style={buttonStyle('#ef4444')} onClick={() => onDecision(request.id, 'rejected')}>Reject</button>
        <button style={buttonStyle('rgba(255,255,255,0.05)')} onClick={() => onDecision(request.id, 'request_changes')}>Changes</button>
        <button style={buttonStyle('#10b981')} onClick={() => onDecision(request.id, 'approved')}>Approve</button>
      </div>
    </div>
  );
}
