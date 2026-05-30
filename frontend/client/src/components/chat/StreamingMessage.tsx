import { useEffect, useRef } from 'react';
import { Bot } from 'lucide-react';

interface StreamingMessageProps {
  content: string;
  isActive: boolean;
}

export function StreamingMessage({ content, isActive }: StreamingMessageProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [content]);

  if (!isActive && !content) return null;

  return (
    <div className="flex justify-start mb-3">
      <div className="flex gap-2 max-w-[85%] md:max-w-[70%]">
        <div className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-slate-100">
          <Bot size={16} className="text-slate-600" />
        </div>
        <div className="p-3 md:p-4 rounded-2xl bg-slate-100 text-slate-900 rounded-tl-none">
          {content ? (
            <p className="text-sm md:text-base leading-relaxed whitespace-pre-wrap break-words">
              {content}
              {isActive && (
                <span className="inline-block w-1.5 h-4 bg-slate-400 ml-0.5 animate-pulse align-middle" />
              )}
            </p>
          ) : isActive ? (
            <div className="flex items-center gap-1.5 py-1">
              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          ) : null}
        </div>
      </div>
      <div ref={bottomRef} />
    </div>
  );
}
