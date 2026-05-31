import { useState, useRef, useEffect } from 'react';
import { Send, Square, Paperclip, Mic, Image as ImageIcon } from 'lucide-react';
import type { ChatAttachment } from '../../lib/types';

interface ComposerProps {
  onSend: (text: string, attachments: ChatAttachment[]) => void;
  disabled?: boolean;
  onCancel?: () => void;
  placeholder?: string;
}

export function Composer({ onSend, disabled, onCancel, placeholder }: ComposerProps) {
  const [text, setText] = useState('');
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!text.trim() && attachments.length === 0) return;
    onSend(text, attachments);
    setText('');
    setAttachments([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [text]);

  return (
    <div className="p-4 bg-white border-t border-border-base shrink-0">
      <div className="max-w-4xl mx-auto relative flex flex-col gap-2">
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {attachments.map((at, i) => (
              <div key={i} className="relative w-16 h-16 rounded-lg border border-border-base overflow-hidden bg-slate-50 group">
                {at.preview ? (
                  <img src={at.preview} alt="upload preview" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-slate-400">
                    <Paperclip size={20} />
                  </div>
                )}
                <button
                  onClick={() => setAttachments(prev => prev.filter((_, idx) => idx !== i))}
                  className="absolute top-1 right-1 p-0.5 bg-black/50 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Square size={10} />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="relative group transition-all duration-200">
          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder || "Type a message..."}
            className={`
              w-full bg-slate-50/50 border border-border-base rounded-2xl py-3 pl-4 pr-24 
              focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary focus:bg-white
              transition-all resize-none text-sm leading-relaxed
              ${disabled ? 'opacity-50' : ''}
            `}
          />

          <div className="absolute right-2 bottom-2 flex items-center gap-1">
            <button
              className="p-2 text-slate-400 hover:text-slate-600 rounded-xl transition-colors"
              title="Attach files (Optional)"
              disabled={disabled}
            >
              <Paperclip size={18} />
            </button>
            
            {disabled && onCancel ? (
              <button
                onClick={onCancel}
                className="p-2 bg-destructive/10 text-destructive hover:bg-destructive hover:text-white rounded-xl transition-all shadow-sm"
                title="Cancel run"
              >
                <Square size={18} fill="currentColor" />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={disabled || (!text.trim() && attachments.length === 0)}
                className={`
                  p-2 rounded-xl transition-all shadow-sm
                  ${text.trim() || attachments.length > 0 
                    ? 'bg-primary text-white hover:bg-primary-dark shadow-primary/20' 
                    : 'bg-slate-100 text-slate-400'}
                `}
              >
                <Send size={18} fill={text.trim() ? "currentColor" : "none"} />
              </button>
            )}
          </div>
        </div>
        
        <div className="flex items-center justify-between px-2">
          <div className="flex gap-4">
            <button className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 hover:text-primary transition-colors uppercase tracking-tight">
              <Mic size={12} />
              Voice
            </button>
            <button className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 hover:text-primary transition-colors uppercase tracking-tight">
              <ImageIcon size={12} />
              Vision
            </button>
          </div>
          <div className="text-[10px] text-slate-400 font-medium">
            Shift + Enter for new line
          </div>
        </div>
      </div>
    </div>
  );
}
