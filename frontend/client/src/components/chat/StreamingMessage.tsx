import { Bot } from 'lucide-react';
import { ToolActivityTimeline } from './ToolActivityTimeline';
import type { ToolActivityItem } from '../../lib/types';

interface StreamingMessageProps {
  content: string;
  activities: ToolActivityItem[];
}

export function StreamingMessage({ content, activities }: StreamingMessageProps) {
  return (
    <div className="flex gap-4 p-4 lg:p-6 bg-slate-50/50">
      <div className="w-8 h-8 lg:w-10 lg:h-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0 shadow-sm">
        <Bot size={20} className="text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[10px] font-black uppercase text-primary tracking-widest mb-1.5 opacity-60">
          Agent Response
        </div>
        <div className="prose prose-slate prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-slate-900 prose-pre:text-slate-100">
          {content || (activities.length > 0 && !content ? (
            <span className="text-slate-400 italic">Processing...</span>
          ) : null)}
          {content}
          <span className="inline-block w-2 h-4 bg-primary/40 ml-1 animate-pulse" />
        </div>
        <ToolActivityTimeline activities={activities} />
      </div>
    </div>
  );
}
