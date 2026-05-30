import { Wrench, Brain, ShieldCheck, Circle, CheckCircle2, XCircle, Clock } from 'lucide-react';
import type { ToolActivityItem } from '../../lib/types';

interface ToolActivityTimelineProps {
  items: ToolActivityItem[];
  compact?: boolean;
}

function statusIcon(status: string) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 size={14} className="text-green-500" />;
    case 'failed':
      return <XCircle size={14} className="text-red-500" />;
    case 'running':
    case 'in_progress':
      return <Clock size={14} className="text-blue-500 animate-pulse" />;
    case 'approval_required':
      return <ShieldCheck size={14} className="text-amber-500" />;
    default:
      return <Circle size={14} className="text-slate-300" />;
  }
}

function itemIcon(type: string) {
  switch (type) {
    case 'tool_call':
      return <Wrench size={14} className="text-violet-500" />;
    case 'memory_read':
      return <Brain size={14} className="text-cyan-500" />;
    case 'approval_required':
      return <ShieldCheck size={14} className="text-amber-500" />;
    case 'step':
      return <Circle size={14} className="text-blue-400" />;
    default:
      return <Circle size={14} className="text-slate-400" />;
  }
}

function typeLabel(type: string) {
  switch (type) {
    case 'tool_call': return 'Tool Call';
    case 'memory_read': return 'Memory';
    case 'approval_required': return 'Approval';
    case 'step': return 'Step';
    default: return 'Event';
  }
}

export function ToolActivityTimeline({ items, compact = false }: ToolActivityTimelineProps) {
  if (items.length === 0) return null;

  if (compact) {
    return (
      <div className="flex flex-wrap gap-1.5 my-1">
        {items.map(item => (
          <span
            key={item.id}
            className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-50 border border-slate-100 rounded-full text-xs text-slate-500"
          >
            {itemIcon(item.type)}
            {item.name || typeLabel(item.type)}
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-3">
      <div className="max-w-[85%] md:max-w-[70%] ml-10">
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-3 space-y-2">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Activity</div>
          {items.map(item => (
            <div key={item.id} className="flex items-start gap-2 text-xs">
              {itemIcon(item.type)}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-slate-600">
                    {item.name || typeLabel(item.type)}
                  </span>
                  {statusIcon(item.status)}
                </div>
                {item.detail && (
                  <p className="text-slate-400 mt-0.5 truncate">{item.detail}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export { statusIcon, itemIcon, typeLabel };
