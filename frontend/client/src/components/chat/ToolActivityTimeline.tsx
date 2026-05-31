import { Bot, User, Terminal, Database, ShieldAlert, Cpu } from 'lucide-react';
import type { ToolActivityItem } from '../../lib/types';

interface ToolActivityTimelineProps {
  activities: ToolActivityItem[];
}

export function ToolActivityTimeline({ activities }: ToolActivityTimelineProps) {
  if (activities.length === 0) return null;

  return (
    <div className="mt-3 space-y-2.5">
      {activities.map((item) => (
        <div key={item.id} className="flex gap-3 animate-in fade-in slide-in-from-left-2 duration-300">
          <div className="flex flex-col items-center shrink-0">
            <div className={`
              w-6 h-6 rounded-lg flex items-center justify-center border shadow-sm
              ${item.type === 'tool_call' ? 'bg-indigo-50 border-indigo-100 text-indigo-600' : 
                item.type === 'memory_read' ? 'bg-emerald-50 border-emerald-100 text-emerald-600' :
                item.type === 'approval_required' ? 'bg-amber-50 border-amber-100 text-amber-600' :
                'bg-slate-50 border-slate-200 text-slate-500'}
            `}>
              {item.type === 'tool_call' && <Terminal size={12} />}
              {item.type === 'memory_read' && <Database size={12} />}
              {item.type === 'approval_required' && <ShieldAlert size={12} />}
              {item.type === 'step' && <Cpu size={12} />}
            </div>
            <div className="w-0.5 flex-1 bg-slate-100 min-h-[4px] last:hidden mt-2" />
          </div>

          <div className="flex-1 min-w-0 py-0.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-bold text-text-base uppercase tracking-wider truncate">
                {item.name}
              </span>
              <span className={`
                text-[9px] font-black uppercase px-1.5 py-0.5 rounded-full tracking-widest border
                ${item.status === 'running' ? 'bg-blue-50 text-blue-600 border-blue-100 animate-pulse' :
                  item.status === 'completed' || item.status === 'success' ? 'bg-emerald-50 text-emerald-600 border-emerald-100' :
                  item.status === 'approval_required' ? 'bg-amber-50 text-amber-600 border-amber-100' :
                  'bg-slate-100 text-slate-500 border-slate-200'}
              `}>
                {item.status}
              </span>
            </div>
            {item.detail && (
              <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed font-mono truncate">
                {item.detail}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
