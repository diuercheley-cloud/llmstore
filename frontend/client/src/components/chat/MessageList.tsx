import { useEffect, useRef } from 'react';
import { User, Bot, Terminal, Database } from 'lucide-react';
import type { SessionMessage, ToolActivityItem } from '../../lib/types';
import { StreamingMessage } from './StreamingMessage';

interface MessageListProps {
  messages: SessionMessage[];
  streamingContent: string;
  streamActivity: ToolActivityItem[];
  isStreaming: boolean;
}

export function MessageList({ messages, streamingContent, streamActivity, isStreaming }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent, streamActivity]);

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-slate-50/30">
        <div className="w-16 h-16 rounded-2xl bg-white shadow-sm border border-border-base flex items-center justify-center mb-4">
          <Bot size={32} className="text-primary/40" />
        </div>
        <h2 className="text-lg font-bold text-text-base">Ready to assist</h2>
        <p className="text-sm text-slate-500 max-w-xs mt-1">
          Select an agent and send a message to start a new persistent conversation.
        </p>
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto bg-white">
      <div className="flex flex-col">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-4 p-4 lg:p-6 transition-colors ${
              msg.role === 'assistant' ? 'bg-slate-50/50' : 'bg-white'
            }`}
          >
            <div className={`
              w-8 h-8 lg:w-10 lg:h-10 rounded-xl flex items-center justify-center shrink-0 shadow-sm
              ${msg.role === 'assistant' ? 'bg-primary/10 text-primary' : 'bg-slate-100 text-slate-500'}
            `}>
              {msg.role === 'assistant' ? <Bot size={20} /> : <User size={20} />}
            </div>
            <div className="flex-1 min-w-0">
              <div className={`
                text-[10px] font-black uppercase tracking-widest mb-1.5 opacity-60
                ${msg.role === 'assistant' ? 'text-primary' : 'text-slate-500'}
              `}>
                {msg.role === 'assistant' ? 'Agent Response' : 'Your Message'}
              </div>
              <div className="prose prose-slate prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-slate-900 prose-pre:text-slate-100 whitespace-pre-wrap">
                {msg.content}
              </div>
              
              {/* If it's a message from tool or has specific metadata, we could show it here */}
              {msg.metadata?.tool_calls && (
                <div className="mt-4 p-3 rounded-lg bg-indigo-50/50 border border-indigo-100 flex items-center gap-3">
                  <Terminal size={14} className="text-indigo-500" />
                  <span className="text-xs font-medium text-indigo-700">Tool execution completed</span>
                </div>
              )}
            </div>
          </div>
        ))}

        {isStreaming && (
          <StreamingMessage 
            content={streamingContent} 
            activities={streamActivity} 
          />
        )}
      </div>
    </div>
  );
}
