import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Terminal, ShieldAlert } from 'lucide-react';
import { AgentRunTimelineComponent } from '../../components/agents/AgentRunTimelineComponent';
import { AgentStatusBadge } from '../../components/agents/AgentStatusBadge';

export default function AgentRunTimeline() {
  const { id } = useParams();

  // Mock data
  const run = {
    id: id || "run_abc123",
    agent: "Support Triage",
    status: "failed",
    started_at: "2026-05-21T10:30:00Z",
    failure_reason: "Policy denial: Destructive tool 'delete_database' requires human approval.",
    timeline: [
      { id: "1", timestamp: "2026-05-21T10:30:01Z", type: "event", event_type: "run_started", payload: { "tenant": "t1" } } as any,
      { id: "2", timestamp: "2026-05-21T10:30:02Z", type: "step", step_number: 1, step_type: "model_call", status: "success", latency_ms: 1200 },
      { id: "3", timestamp: "2026-05-21T10:30:03Z", type: "step", step_number: 2, step_type: "tool_call", status: "failed", error: "Policy denial: Destructive tool requires approval.", payload: { "tool_name": "delete_database" } },
      { id: "4", timestamp: "2026-05-21T10:30:03Z", type: "event", event_type: "policy_denial", payload: { "reason": "Destructive tool requires human approval." } },
    ]
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
      <header>
        <Link to="/agents/runs" className="inline-flex items-center gap-2 text-sm font-bold text-muted-foreground hover:text-primary transition-colors mb-4">
          <ArrowLeft size={16} /> Voltar para Execuções
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-black tracking-tight flex items-center gap-3">
              Run <span className="text-primary font-mono text-2xl">{run.id}</span>
            </h1>
            <p className="text-muted-foreground mt-2 text-lg">Detalhes da execução do agente <span className="font-bold">{run.agent}</span>.</p>
          </div>
          <AgentStatusBadge status={run.status} />
        </div>
      </header>

      {run.failure_reason && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-2xl p-4 flex gap-4 text-destructive">
          <ShieldAlert className="w-6 h-6 shrink-0" />
          <div>
            <h4 className="font-bold uppercase tracking-widest text-xs mb-1">Falha na Execução</h4>
            <p className="text-sm">{run.failure_reason}</p>
          </div>
        </div>
      )}

      <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-sm">
        <div className="p-6 border-b border-border bg-secondary/50 flex justify-between items-center">
           <h3 className="font-black uppercase tracking-widest text-foreground">Timeline de Eventos</h3>
           <Terminal className="w-5 h-5 text-muted-foreground" />
        </div>
        <div className="p-6">
          <AgentRunTimelineComponent items={run.timeline} />
        </div>
      </div>
    </div>
  );
}
