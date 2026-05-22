import React from 'react';
import { Activity, Ban, CheckCircle, Clock, AlertTriangle, Shield } from 'lucide-react';

interface AgentStatusBadgeProps {
  status: string;
}

export function AgentStatusBadge({ status }: AgentStatusBadgeProps) {
  const normalizedStatus = status.toLowerCase();
  
  if (['active', 'completed', 'approved'].includes(normalizedStatus)) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider bg-green-500/10 text-green-600">
        <CheckCircle className="w-3.5 h-3.5" />
        {status}
      </span>
    );
  }
  
  if (['failed', 'rejected', 'cancelled', 'denied'].includes(normalizedStatus)) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider bg-destructive/10 text-destructive">
        <Ban className="w-3.5 h-3.5" />
        {status}
      </span>
    );
  }
  
  if (['running', 'executing'].includes(normalizedStatus)) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider bg-primary/10 text-primary animate-pulse">
        <Activity className="w-3.5 h-3.5" />
        {status}
      </span>
    );
  }
  
  if (['waiting_approval', 'pending_approval', 'review'].includes(normalizedStatus)) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider bg-yellow-500/10 text-yellow-600">
        <Shield className="w-3.5 h-3.5" />
        {status}
      </span>
    );
  }

  // Default / Pending / Draft
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider bg-secondary text-muted-foreground">
      <Clock className="w-3.5 h-3.5" />
      {status}
    </span>
  );
}
