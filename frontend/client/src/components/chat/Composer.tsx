import { useState, useRef } from 'react';
import { Send, Paperclip, X, Loader2 } from 'lucide-react';
import type { ChatAttachment } from '../../lib/types';

interface ComposerProps {
  onSend: (text: string, attachments?: ChatAttachment[]) => void;
  disabled: boolean;
  onCancel?: () => void;
  placeholder?: string;
}

export function Composer({ onSend, disabled, onCancel, placeholder }: ComposerProps) {
  const [text, setText] = useState('');
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const MAX_FILES = 5;

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed && attachments.length === 0) return;
    onSend(trimmed, attachments.length > 0 ? attachments : undefined);
    setText('');
    setAttachments([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const remaining = MAX_FILES - attachments.length;
    const newAttachments = files.slice(0, remaining).map(file => ({
      file,
      mimeType: file.type,
    }));
    setAttachments(prev => [...prev, ...newAttachments]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="p-4 border-t border-border-base bg-white">
      {attachments.length > 0 && (
        <div className="flex gap-2 flex-wrap mb-3 max-w-4xl mx-auto">
          {attachments.map((att, i) => (
            <div key={i} className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 rounded-lg text-xs text-slate-600">
              <span className="truncate max-w-[120px]">{att.file.name}</span>
              <button
                onClick={() => removeAttachment(i)}
                className="p-0.5 hover:bg-slate-200 rounded"
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
      <div className="flex gap-2 max-w-4xl mx-auto items-end">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={handleFileSelect}
          accept="image/*,.pdf,.txt,.csv,.json,.md"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || attachments.length >= MAX_FILES}
          className="p-3 rounded-full text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors disabled:opacity-30 shrink-0"
          title="Attach file"
        >
          <Paperclip size={20} />
        </button>
        <textarea
          ref={textareaRef}
          className="flex-1 resize-none px-4 py-3 bg-white border border-border-base rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-sm md:text-base min-h-[44px] max-h-[160px]"
          placeholder={placeholder || 'Type your message... (Shift+Enter for newline)'}
          value={text}
          onChange={handleTextChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
        />
        {disabled && onCancel ? (
          <button
            onClick={onCancel}
            className="p-3 rounded-full bg-red-500 text-white hover:bg-red-600 transition-colors shrink-0"
            title="Cancel"
          >
            <X size={20} />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={disabled || (!text.trim() && attachments.length === 0)}
            className={`p-3 rounded-full transition-colors shrink-0 shadow-lg shadow-primary/20 ${
              disabled || (!text.trim() && attachments.length === 0)
                ? 'bg-slate-300 cursor-not-allowed shadow-none'
                : 'bg-primary text-white hover:bg-primary/90'
            }`}
          >
            {disabled ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
          </button>
        )}
      </div>
    </div>
  );
}
