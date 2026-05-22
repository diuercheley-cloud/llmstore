import React from 'react';
import { AlertTriangle, Info, ShieldAlert, ShieldCheck } from 'lucide-react';

interface AgentRiskBadgeProps {
  level: string;
}

export function AgentRiskBadge({ level }: AgentRiskBadgeProps) {
  const normalized = level.toLowerCase();
  
  if (normalized === 'critical') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider bg-red-900 text-red-100">
        <ShieldAlert className="w-3.5 h-3.5" />
        Critical
      </span>
    );
  }
  
  if (normalized === 'high') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider bg-red-500/10 text-red-600">
        <AlertTriangle className="w-3.5 h-3.5" />
        High Risk
      </span>
    );
  }
  
  if (normalized === 'medium') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider bg-yellow-500/10 text-yellow-600">
        <Info className="w-3.5 h-3.5" />
        Medium
      </span>
    );
  }
  
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider bg-blue-500/10 text-blue-600">
      <ShieldCheck className="w-3.5 h-3.5" />
      Low Risk
    </span>
  );
}
