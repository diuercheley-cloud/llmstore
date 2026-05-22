import React, { useState } from 'react';
import { ShieldAlert, Search } from 'lucide-react';
import { ApprovalDecisionModal } from '../../components/agents/ApprovalDecisionModal';
import { AgentStatusBadge } from '../../components/agents/AgentStatusBadge';

export default function AgentApprovals() {
  const [selectedRequest, setSelectedRequest] = useState<any>(null);

  const approvals = [
    { id: "req_123", agent: "DB Admin Ops", run_id: "run_ghi789", tool: "delete_database", risk: "critical", status: "pending", requested_at: "2026-05-21T10:30:00Z" },
    { id: "req_456", agent: "Billing Auditor", run_id: "run_jkl012", tool: "refund_customer", risk: "high", status: "pending", requested_at: "2026-05-21T09:45:00Z" }
  ];

  const handleApprove = async (reason: string) => {
    // API call to approve
    console.log("Approved", selectedRequest?.id, reason);
    setSelectedRequest(null);
  };

  const handleReject = async (reason: string) => {
    // API call to reject
    console.log("Rejected", selectedRequest?.id, reason);
    setSelectedRequest(null);
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
      <header>
        <h1 className="text-4xl font-black tracking-tight flex items-center gap-3">
          Agent <span className="text-primary">Approvals</span>
        </h1>
        <p className="text-muted-foreground mt-2 text-lg">Human-in-the-loop (HITL) para ações sensíveis de agentes.</p>
      </header>

      <div className="bg-card border border-border rounded-3xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-border bg-secondary/30 flex justify-between items-center gap-4">
           <div className="relative flex-1 max-w-md">
             <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
             <input type="text" placeholder="Buscar aprovações pendentes..." className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-lg text-sm focus:ring-2 focus:ring-primary outline-none" />
           </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-secondary/30 text-muted-foreground text-[10px] font-black uppercase tracking-widest border-b border-border">
                <th className="px-6 py-4">Requisição ID</th>
                <th className="px-6 py-4">Agente</th>
                <th className="px-6 py-4">Ferramenta</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Data</th>
                <th className="px-6 py-4 text-right">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {approvals.map(req => (
                <tr key={req.id} className="hover:bg-secondary/50 transition-colors">
                  <td className="px-6 py-4 font-mono text-xs text-muted-foreground">{req.id}</td>
                  <td className="px-6 py-4 font-bold text-sm">{req.agent}</td>
                  <td className="px-6 py-4 font-mono text-xs text-primary">{req.tool}</td>
                  <td className="px-6 py-4"><AgentStatusBadge status={req.status} /></td>
                  <td className="px-6 py-4 text-xs text-muted-foreground">{new Date(req.requested_at).toLocaleString()}</td>
                  <td className="px-6 py-4 text-right">
                    <button 
                      onClick={() => setSelectedRequest(req)}
                      className="bg-foreground text-background font-bold px-4 py-2 rounded-xl text-xs hover:opacity-90 transition-opacity"
                    >
                      Revisar
                    </button>
                  </td>
                </tr>
              ))}
              {approvals.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center p-8 text-muted-foreground italic">Nenhuma aprovação pendente no momento.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <ApprovalDecisionModal 
        isOpen={!!selectedRequest}
        onClose={() => setSelectedRequest(null)}
        onApprove={handleApprove}
        onReject={handleReject}
        title={`Aprovação: ${selectedRequest?.tool}`}
        isDestructive={selectedRequest?.risk === 'critical'}
      />
    </div>
  );
}
