import React from 'react';
import { useQueries } from '@tanstack/react-query';
import { Bot, Activity, ShieldCheck, Database, LayoutDashboard, FolderOpen } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../../lib/api';

export default function AgentsOverview() {
  const [registryQuery, observabilityQuery, approvalsQuery] = useQueries({
    queries: [
      {
        queryKey: ['agents-overview-registry'],
        queryFn: () => api.listAgentRegistry(),
      },
      {
        queryKey: ['agents-overview-observability'],
        queryFn: async () => (await api.get('/admin/agents/observability/overview')).data,
      },
      {
        queryKey: ['agents-overview-approvals'],
        queryFn: () => api.listPendingApprovals(),
      },
    ],
  });

  const activeAgents = registryQuery.data?.length ?? 0;
  const totalRuns = observabilityQuery.data?.total_runs ?? 0;
  const pendingApprovals = approvalsQuery.data?.items?.length ?? 0;
  const totalSteps = (observabilityQuery.data?.recent_runs ?? []).reduce(
    (sum: number, run: { total_steps?: number }) => sum + (run.total_steps ?? 0),
    0,
  );
  const stats = [
    { title: "Agentes Ativos", value: String(activeAgents), icon: Bot, link: "/agents/registry" },
    { title: "Execuções Recentes", value: String(totalRuns), icon: Activity, link: "/observability/agents" },
    { title: "Aprovações Pendentes", value: String(pendingApprovals), icon: ShieldCheck, link: "/agents/approvals" },
    { title: "Passos Observados", value: String(totalSteps), icon: Database, link: "/observability/agents" },
    { title: "Shared Workspaces", value: "Live", icon: FolderOpen, link: "/agents/workspaces" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
      <header>
        <h1 className="text-4xl font-black tracking-tight flex items-center gap-3">
          <LayoutDashboard className="text-primary w-8 h-8" />
          Agent <span className="text-primary">Overview</span>
        </h1>
        <p className="text-muted-foreground mt-2 text-lg">Visão geral do ecossistema de agentes inteligentes.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <Link key={idx} to={stat.link} className="bg-card border border-border p-6 rounded-3xl shadow-sm hover:border-primary/50 hover:shadow-md transition-all group">
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 bg-secondary/50 rounded-xl group-hover:bg-primary/10 transition-colors">
                  <Icon className="w-6 h-6 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
              </div>
              <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-widest">{stat.title}</h3>
              <p className="text-3xl font-black text-foreground mt-2">{stat.value}</p>
            </Link>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
           <h3 className="font-black uppercase tracking-widest text-muted-foreground mb-4">Atividade Recente</h3>
           <div className="text-sm text-muted-foreground italic text-center p-10 border border-dashed border-border rounded-xl">
             {(observabilityQuery.data?.recent_runs?.length ?? 0) === 0
               ? 'Nenhuma atividade recente detectada.'
               : `${observabilityQuery.data.recent_runs.length} execuções recentes disponíveis em Observability.`}
           </div>
        </div>

        <div className="bg-card border border-border rounded-3xl p-6 shadow-sm">
           <h3 className="font-black uppercase tracking-widest text-muted-foreground mb-4">Avisos de Governança</h3>
           <div className="space-y-3">
              <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl flex gap-3 text-sm text-yellow-600">
                <ShieldCheck className="w-5 h-5 shrink-0" />
                <div>
                  <span className="font-bold block">Baseline Recomendado</span>
                  <span className="opacity-80">{pendingApprovals} aprovações humanas aguardando decisão.</span>
                </div>
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}
