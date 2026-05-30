import { useEffect, useRef } from 'react';
import { User, Bot } from 'lucide-react';
import type { SessionMessage } from '../../lib/types';
import { ToolActivityTimeline } from './ToolActivityTimeline';
import type { ToolActivityItem } from '../../lib/types';

interface MessageListProps {
  messages: SessionMessage[];
  streamingContent: string;
  streamActivity: ToolActivityItem[];
  isStreaming: boolean;
}

export function MessageList({ messages, streamingContent, streamActivity, isStreaming }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, isStreaming]);

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
          <Bot size={32} className="text-primary" />
        </div>
        <h3 className="text-lg font-semibold text-text-base mb-2">How can I help you?</h3>
        <p className="text-sm text-slate-500 max-w-sm">
          Start a conversation by typing a message below. Your chat history will appear here.
        </p>
      </div>
    );
  }

  const renderMessage = (msg: SessionMessage) => {
    const isUser = msg.role === 'user';
    const isSystem = msg.role === 'system';
    const isTool = msg.role === 'tool';

    if (isSystem) {
      return (
        <div key={msg.id} className="flex justify-center my-2">
          <div className="text-xs text-slate-400 bg-slate-50 px-3 py-1 rounded-full">
            {msg.content}
          </div>
        </div>
      );
    }

    if (isTool) {
      return null;
    }

    return (
      <div key={msg.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
        <div className={`flex gap-2 max-w-[85%] md:max-w-[70%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            isUser ? 'bg-primary/10' : 'bg-slate-100'
          }`}>
            {isUser
              ? <User size={16} className="text-primary" />
              : <Bot size={16} className="text-slate-600" />
            }
          </div>
          <div className={`p-3 md:p-4 rounded-2xl ${
            isUser
              ? 'bg-primary text-white rounded-tr-none'
              : 'bg-slate-100 text-slate-900 rounded-tl-none'
          }`}>
            <p className="text-sm md:text-base leading-relaxed whitespace-pre-wrap break-words">{msg.content}</p>
            {msg.metadata && Object.keys(msg.metadata).length > 0 && (
              <div className={`mt-2 text-xs ${isUser ? 'text-white/70' : 'text-slate-400'}`}>
                {typeof msg.metadata['tokens'] === 'number' && <span>{msg.metadata['tokens']} tokens</span>}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-1">
      {messages.map(renderMessage)}

      {isStreaming && streamActivity.length > 0 && (
        <ToolActivityTimeline items={streamActivity} />
      )}

      {isStreaming && streamingContent && (
        <div className="flex justify-start mb-3">
          <div className="flex gap-2 max-w-[85%] md:max-w-[70%]">
            <div className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-slate-100">
              <Bot size={16} className="text-slate-600" />
            </div>
            <div className="p-3 md:p-4 rounded-2xl bg-slate-100 text-slate-900 rounded-tl-none">
              <p className="text-sm md:text-base leading-relaxed whitespace-pre-wrap break-words">
                {streamingContent}
                <span className="inline-block w-1.5 h-4 bg-slate-400 ml-0.5 animate-pulse align-middle" />
              </p>
            </div>
          </div>
        </div>
      )}

      {isStreaming && !streamingContent && (
        <div className="flex justify-start mb-3">
          <div className="flex gap-2">
            <div className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-slate-100">
              <Bot size={16} className="text-slate-600" />
            </div>
            <div className="px-4 py-3 rounded-2xl bg-slate-100 rounded-tl-none flex items-center gap-1.5">
              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
