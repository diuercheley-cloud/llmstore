import { useState, useEffect } from 'react';
import { Plus, MessageSquare, Trash2, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';
import type { Session } from '../../lib/types';

interface SessionListProps {
  agentId: string | null;
  activeSessionId: string | null;
  onSelect: (session: Session) => void;
  onNew: () => void;
}

export function SessionList({ agentId, activeSessionId, onSelect, onNew }: SessionListProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!agentId) { setSessions([]); return; }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.listSessions(agentId);
        if (!cancelled) setSessions(data);
      } catch (err: any) {
        if (!cancelled) setError(err.message || 'Failed to load sessions');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [agentId]);

  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    try {
      await api.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
    } catch {
      // silently fail
    }
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border-base">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Conversations</span>
        <button
          onClick={onNew}
          disabled={!agentId}
          className="p-1.5 rounded-md hover:bg-slate-100 text-slate-500 hover:text-primary transition-colors disabled:opacity-30"
          title="New conversation"
        >
          <Plus size={16} />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {!agentId && (
          <div className="p-4 text-center text-sm text-slate-400">
            Select an agent to view conversations
          </div>
        )}
        {loading && (
          <div className="p-4 flex justify-center">
            <Loader2 size={20} className="animate-spin text-slate-400" />
          </div>
        )}
        {error && (
          <div className="p-3 m-2 text-xs text-red-500 bg-red-50 rounded-lg">{error}</div>
        )}
        {!loading && !error && agentId && sessions.length === 0 && (
          <div className="p-4 text-center text-sm text-slate-400">
            No conversations yet
          </div>
        )}
        {sessions.map(session => (
          <button
            key={session.id}
            onClick={() => onSelect(session)}
            className={`w-full flex items-center gap-2 px-3 py-2.5 text-left transition-colors group ${
              session.id === activeSessionId
                ? 'bg-primary/5 border-r-2 border-primary'
                : 'hover:bg-slate-50'
            }`}
          >
            <MessageSquare size={14} className="text-slate-400 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-sm truncate text-text-base">
                {session.title || 'Untitled'}
              </div>
              <div className="text-xs text-slate-400">
                {session.last_message_at ? formatTime(session.last_message_at) : formatTime(session.created_at)}
              </div>
            </div>
            <button
              onClick={(e) => handleDelete(e, session.id)}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 transition-all"
              title="Delete"
            >
              <Trash2 size={12} />
            </button>
          </button>
        ))}
      </div>
    </div>
  );
}
