import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../../lib/api';
import ApprovalDetail from './ApprovalDetail';
import { LoadingCard } from '../../../components/ui-feedback';

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

export default function ApprovalPortal() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filterTenant, setFilterTenant] = useState('all');

  const { data, isLoading } = useQuery({
    queryKey: ['agent-approvals'],
    queryFn: () => api.listPendingApprovals()
  });

  const requests: ApprovalRequest[] = data?.items || [];

  const decideMutation = useMutation({
    mutationFn: async ({ id, decision }: { id: string, decision: string }) => {
      return api.decideApproval(id, decision);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-approvals'] });
      setSelectedId(null);
    }
  });

  const handleDecision = (id: string, decision: string) => {
    decideMutation.mutate({ id, decision });
  };

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    height: '100vh',
    backgroundColor: '#0b0f19',
    color: '#f3f4f6',
    fontFamily: '"Outfit", "Inter", sans-serif',
  };

  const listAreaStyle: React.CSSProperties = {
    flex: 1,
    padding: '32px',
    overflowY: 'auto',
    borderRight: '1px solid rgba(255, 255, 255, 0.08)',
  };

  const headerStyle: React.CSSProperties = {
    fontSize: '24px',
    fontWeight: 'bold',
    marginBottom: '24px',
    background: 'linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  };

  const cardStyle = (req: ApprovalRequest): React.CSSProperties => ({
    background: 'rgba(15, 23, 42, 0.6)',
    border: selectedId === req.id ? '1px solid #f59e0b' : '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '10px',
    padding: '20px',
    marginBottom: '16px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  });

  const riskBadge = (risk: string): React.CSSProperties => {
    let color = '#ef4444';
    let bg = 'rgba(239, 68, 68, 0.1)';
    if (risk === 'critical') {
      color = '#dc2626';
      bg = 'rgba(220, 38, 38, 0.2)';
    } else if (risk === 'medium') {
      color = '#f59e0b';
      bg = 'rgba(245, 158, 11, 0.1)';
    }

    return {
      fontSize: '11px',
      fontWeight: 'bold',
      color,
      backgroundColor: bg,
      padding: '2px 8px',
      borderRadius: '12px',
      textTransform: 'uppercase',
    };
  };

  const selectedRequest = requests.find(r => r.id === selectedId);

  if (isLoading) return <LoadingCard />;

  return (
    <div style={containerStyle}>
      <div style={listAreaStyle}>
        <h1 style={headerStyle}>Human-in-the-Loop Approval Inbox</h1>
        <div>
          {requests.length === 0 ? (
            <p style={{ color: 'rgba(255,255,255,0.4)', textAlign: 'center', marginTop: '40px' }}>
              No pending approval requests. All systems clear!
            </p>
          ) : (
            requests.map(req => (
              <div key={req.id} style={cardStyle(req)} onClick={() => setSelectedId(req.id)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontWeight: 600, fontSize: '15px' }}>{req.agent_name}</span>
                  <span style={riskBadge(req.risk_level)}>{req.risk_level}</span>
                </div>
                <p style={{ margin: '0 0 12px 0', fontSize: '13px', color: 'rgba(255,255,255,0.7)' }}>{req.reason}</p>
                <div style={{ display: 'flex', gap: '16px', fontSize: '11px', color: 'rgba(255,255,255,0.4)' }}>
                  <span>Tenant: {req.tenant_id}</span>
                  <span>Expires: {new Date(req.expires_at).toLocaleString()}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
      <div style={{ width: '450px', background: 'rgba(10, 17, 32, 0.95)', display: 'flex', flexDirection: 'column' }}>
        {selectedRequest ? (
          <ApprovalDetail approval={selectedRequest} />
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '14px' }}>
            Select a request to review details
          </div>
        )}
      </div>
    </div>
  );
}
