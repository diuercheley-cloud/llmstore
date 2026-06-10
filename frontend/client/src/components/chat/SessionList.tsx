import { useState, useEffect } from 'react';
import { MessageSquare, Plus, Trash2, Clock } from 'lucide-react';
import { api } from '../../lib/api';
import type { Session } from '../../lib/types';
import { toast } from 'sonner';

interface SessionListProps {
  agentId: string | null;
  activeSessionId: string | null;
  onSelect: (session: Session) => void;
  onNew: () => void;
}

export function SessionList({ agentId, activeSessionId, onSelect, onNew }: SessionListProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadSessions() {
      if (!agentId) return;
      setLoading(true);
      try {
        const list = await api.listSessions(agentId);
        setSessions(list);
      } catch (err) {
        console.error('Failed to load sessions', err);
      } finally {
        setLoading(false);
      }
    }
    loadSessions();
  }, [agentId]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this session?')) return;
    try {
      await api.deleteSession(id);
      setSessions(prev => prev.filter(s => s.id !== id));
      toast.success('Session deleted');
    } catch {
      toast.error('Failed to delete session');
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-50/50">
      <div className="p-3">
        <button
          onClick={onNew}
          disabled={!agentId}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-white border border-dashed border-border-base rounded-xl text-sm font-medium text-slate-600 hover:border-primary/50 hover:text-primary transition-all group disabled:opacity-50"
        >
          <Plus size={16} className="group-hover:rotate-90 transition-transform" />
          New Thread
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        {loading && <div className="p-4 text-center text-xs text-slate-400">Loading history...</div>}
        {!loading && sessions.length === 0 && (
          <div className="p-8 text-center">
            <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-2">
              <MessageSquare size={16} className="text-slate-400" />
            </div>
            <p className="text-xs text-slate-500">No conversations yet</p>
          </div>
        )}
        {sessions.map(session => (
          <button
            key={session.id}
            onClick={() => onSelect(session)}
            className={`
              w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all group text-left
              ${activeSessionId === session.id 
                ? 'bg-white shadow-sm border border-border-base ring-1 ring-primary/5' 
                : 'hover:bg-slate-100/80 border border-transparent'}
            `}
          >
            <div className={`
              w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors
              ${activeSessionId === session.id ? 'bg-primary/10 text-primary' : 'bg-slate-100 text-slate-400'}
            `}>
              <MessageSquare size={16} />
            </div>
            <div className="flex-1 min-w-0">
              <div className={`text-sm truncate ${activeSessionId === session.id ? 'font-semibold text-text-base' : 'text-slate-600'}`}>
                {session.title || 'Untitled Chat'}
              </div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <Clock size={10} className="text-slate-400" />
                <span className="text-[10px] text-slate-400 font-medium">
                  {new Date(session.updated_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            <div className="opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={(e) => handleDelete(e, session.id)}
                className="p-1.5 rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
