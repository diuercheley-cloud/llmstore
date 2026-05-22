import React from 'react';
import { Shield, ShieldAlert, ShieldCheck, HelpCircle } from 'lucide-react';

interface PolicyDecision {
  name: string;
  status: string; // active, disabled, evaluating
}

export function PolicyDecisionPanel({ policies }: { policies: PolicyDecision[] }) {
  if (!policies || policies.length === 0) {
    return (
      <div className="text-sm text-muted-foreground italic p-4 bg-secondary/30 rounded-xl border border-border">
        Nenhuma política de governança aplicada ativamente.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {policies.map((policy, idx) => (
        <div key={idx} className="flex items-center justify-between p-3 bg-card border border-border rounded-xl shadow-sm">
          <div className="flex items-center gap-3">
            {policy.status === 'active' ? (
               <ShieldCheck className="w-5 h-5 text-green-500" />
            ) : policy.status === 'evaluating' ? (
               <HelpCircle className="w-5 h-5 text-yellow-500" />
            ) : (
               <ShieldAlert className="w-5 h-5 text-muted-foreground" />
            )}
            <span className="font-bold text-sm text-foreground">{policy.name}</span>
          </div>
          <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded ${
            policy.status === 'active' ? 'bg-green-500/10 text-green-600' : 
            policy.status === 'evaluating' ? 'bg-yellow-500/10 text-yellow-600' :
            'bg-secondary text-muted-foreground'
          }`}>
            {policy.status}
          </span>
        </div>
      ))}
    </div>
  );
}
