import { useState, useEffect, useCallback, useRef } from 'react';
import { PanelLeftClose, PanelLeftOpen, AlertCircle, RefreshCw, Key } from 'lucide-react';
import { toast } from 'sonner';
import { api, buildWebSocketUrl, setAuthToken, getAuthToken as getToken } from '../lib/api';
import { AgentSelector } from '../components/chat/AgentSelector';
import { SessionList } from '../components/chat/SessionList';
import { MessageList } from '../components/chat/MessageList';
import { Composer } from '../components/chat/Composer';
import type { Agent, Session, SessionMessage, ToolActivityItem, ChatAttachment } from '../lib/types';

let activityCounter = 0;
function nextActivityId(): string {
  return `act-${++activityCounter}`;
}

export function AgentChat() {
  const [token, setTokenState] = useState<string>(() => getToken() || '');
  const [tokenSaved, setTokenSaved] = useState<boolean>(() => !!getToken());
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [streamActivity, setStreamActivity] = useState<ToolActivityItem[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [reconnectCount, setReconnectCount] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const runIdRef = useRef<string | null>(null);

  const handleSaveToken = () => {
    const t = token.trim();
    if (!t) return;
    setAuthToken(t);
    setTokenSaved(true);
    toast.success('API token saved');
  };

  const handleTokenInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSaveToken();
  };

  const loadMessages = useCallback(async (sessionId: string) => {
    try {
      const msgs = await api.getMessages(sessionId);
      setMessages(msgs);
    } catch (err: any) {
      toast.error('Failed to load messages');
    }
  }, []);

  const handleSelectSession = useCallback(async (session: Session) => {
    setActiveSession(session);
    setMessages([]);
    setStreamingContent('');
    setStreamActivity([]);
    setRunError(null);
    if (isStreaming) {
      wsRef.current?.close();
    }
    await loadMessages(session.id);
  }, [loadMessages, isStreaming]);

  const handleNewSession = useCallback(async () => {
    if (!selectedAgent) return;
    try {
      const session = await api.createSession(selectedAgent.id, `Chat with ${selectedAgent.name}`);
      setActiveSession(session);
      setMessages([]);
      setStreamingContent('');
      setStreamActivity([]);
      setRunError(null);
      setMobileSidebarOpen(false);
    } catch (err: any) {
      toast.error(err.message || 'Failed to create session');
    }
  }, [selectedAgent]);

  const handleAgentSelect = useCallback(async (agent: Agent) => {
    setSelectedAgent(agent);
    setActiveSession(null);
    setMessages([]);
    setStreamActivity([]);
    setStreamingContent('');
    setRunError(null);
    if (isStreaming) {
      wsRef.current?.close();
    }
  }, [isStreaming]);

  const processStreamEvent = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      const et = data.event_type;
      const p = data.payload || {};

      if (et === 'step_completed' || et === 'agent_step') {
        const name = p.tool_name || p.step_type || 'Step';
        const status = p.status || 'completed';
        const detail = p.output_preview || p.detail || `Step ${p.step_number || ''}`;
        setStreamActivity(prev => [...prev, {
          id: nextActivityId(),
          type: 'tool_call',
          name,
          status,
          detail,
          timestamp: new Date().toISOString(),
        }]);
        if (p.output_text) {
          setStreamingContent(prev => prev + p.output_text);
        }
      } else if (et === 'tool_call' || et === 'tool_invocation') {
        setStreamActivity(prev => [...prev, {
          id: nextActivityId(),
          type: 'tool_call',
          name: p.tool_name || p.name || 'Tool',
          status: p.status || 'running',
          detail: p.arguments ? JSON.stringify(p.arguments).slice(0, 100) : undefined,
          timestamp: new Date().toISOString(),
        }]);
      } else if (et === 'memory_read' || et === 'memory_access') {
        setStreamActivity(prev => [...prev, {
          id: nextActivityId(),
          type: 'memory_read',
          name: p.collection || p.name || 'Memory',
          status: 'completed',
          detail: p.query || p.summary,
          timestamp: new Date().toISOString(),
        }]);
      } else if (et === 'approval_required' || et === 'waiting_approval') {
        setStreamActivity(prev => [...prev, {
          id: nextActivityId(),
          type: 'approval_required',
          name: p.tool_name || 'Approval Needed',
          status: 'approval_required',
          detail: p.reason || p.description,
          timestamp: new Date().toISOString(),
        }]);
      } else if (et === 'text_delta' || et === 'content_delta' || et === 'token') {
        const text = p.text || p.delta || p.content || '';
        if (text) setStreamingContent(prev => prev + text);
      } else if (et === 'run_completed' || et === 'completed') {
        setIsStreaming(false);
        wsRef.current?.close();
        if (activeSession) loadMessages(activeSession.id);
      } else if (et === 'run_failed' || et === 'failed') {
        setIsStreaming(false);
        setRunError(p.error || p.failure_reason || 'Run failed');
        wsRef.current?.close();
        toast.error('Agent run failed');
      } else if (et === 'run_cancelled') {
        setIsStreaming(false);
        wsRef.current?.close();
        toast.info('Run cancelled');
      } else if (et === 'status' || et === 'run.status') {
        if (p.status === 'completed' || p.status === 'failed' || p.status === 'cancelled') {
          setIsStreaming(false);
          wsRef.current?.close();
          if (p.status === 'completed' && activeSession) loadMessages(activeSession.id);
        }
      }
    } catch {
      // ignore non-JSON messages
    }
  }, [activeSession, loadMessages]);

  const connectWebSocket = useCallback((runId: string, attempt = 0) => {
    const wsUrl = buildWebSocketUrl(runId);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    runIdRef.current = runId;

    ws.onopen = () => {
      setReconnectCount(0);
      setRunError(null);
    };

    ws.onmessage = processStreamEvent;

    ws.onerror = () => {
      setRunError('WebSocket connection error');
    };

    ws.onclose = (ev) => {
      if (isStreaming && attempt < 3 && ev.code !== 1000) {
        const delay = Math.min(1000 * 2 ** attempt, 10000);
        reconnectTimerRef.current = setTimeout(() => {
          setReconnectCount(c => c + 1);
          connectWebSocket(runId, attempt + 1);
        }, delay);
      } else if (attempt >= 3) {
        setIsStreaming(false);
        setRunError('Lost connection to agent. Please try again.');
      }
    };
  }, [processStreamEvent, isStreaming]);

  const handleSend = useCallback(async (text: string, _attachments?: ChatAttachment[]) => {
    if (!selectedAgent) {
      toast.error('Please select an agent first');
      return;
    }

    if (!tokenSaved) {
      toast.error('Please configure your API token first');
      return;
    }

    setIsStreaming(true);
    setStreamingContent('');
    setStreamActivity([]);
    setRunError(null);

    try {
      let sessionId = activeSession?.id;

      if (!sessionId) {
        const session = await api.createSession(selectedAgent.id, text.slice(0, 60));
        sessionId = session.id;
        setActiveSession(session);
      }

      const run = await api.startSessionRun(sessionId, text);
      connectWebSocket(run.run_id);
    } catch (err: any) {
      setIsStreaming(false);
      setRunError(err.message || 'Failed to start run');
      toast.error(err.message || 'Failed to start run');
    }
  }, [selectedAgent, activeSession, tokenSaved, connectWebSocket]);

  const handleCancelRun = useCallback(() => {
    if (runIdRef.current) {
      wsRef.current?.send(JSON.stringify({ command: 'cancel' }));
    }
    wsRef.current?.close();
    setIsStreaming(false);
    toast.info('Cancelling run...');
  }, []);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    };
  }, []);

  const showAuthPrompt = !tokenSaved;

  return (
    <div className="flex h-[calc(100vh-8rem)] md:h-[calc(100vh-10rem)] bg-white border border-border-base rounded-2xl shadow-sm overflow-hidden">
      {/* Mobile sidebar backdrop */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-40
        w-72 bg-white border-r border-border-base
        flex flex-col
        transform transition-transform duration-200 lg:transform-none
        ${mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        ${!sidebarOpen && 'lg:hidden'}
      `}>
        <div className="p-3 border-b border-border-base">
          <AgentSelector
            selectedAgentId={selectedAgent?.id || null}
            onSelect={handleAgentSelect}
          />
        </div>
        <div className="flex-1 overflow-hidden">
          <SessionList
            agentId={selectedAgent?.id || null}
            activeSessionId={activeSession?.id || null}
            onSelect={handleSelectSession}
            onNew={handleNewSession}
          />
        </div>
      </aside>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center gap-2 px-4 py-3 border-b border-border-base bg-white shrink-0">
          {!sidebarOpen && (
            <button
              onClick={() => setSidebarOpen(true)}
              className="hidden lg:flex p-1.5 rounded-md hover:bg-slate-100 text-slate-500"
              title="Show sidebar"
            >
              <PanelLeftOpen size={18} />
            </button>
          )}
          {sidebarOpen && (
            <button
              onClick={() => setSidebarOpen(false)}
              className="hidden lg:flex p-1.5 rounded-md hover:bg-slate-100 text-slate-500"
              title="Hide sidebar"
            >
              <PanelLeftClose size={18} />
            </button>
          )}
          <button
            onClick={() => setMobileSidebarOpen(true)}
            className="lg:hidden p-1.5 rounded-md hover:bg-slate-100 text-slate-500"
          >
            <PanelLeftOpen size={18} />
          </button>
          <div className="flex-1 min-w-0">
            {activeSession ? (
              <div className="truncate text-sm font-medium text-text-base">
                {activeSession.title || 'New conversation'}
              </div>
            ) : selectedAgent ? (
              <div className="truncate text-sm text-slate-500">
                {selectedAgent.name}
              </div>
            ) : (
              <div className="text-sm text-slate-400">Select an agent to start</div>
            )}
          </div>
          {isStreaming && (
            <span className="flex items-center gap-1.5 text-xs text-blue-500">
              <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              Streaming
            </span>
          )}
          {reconnectCount > 0 && (
            <span className="flex items-center gap-1 text-xs text-amber-500">
              <RefreshCw size={12} className="animate-spin" />
              Reconnecting...
            </span>
          )}
        </header>

        {/* Auth Prompt */}
        {showAuthPrompt && (
          <div className="flex flex-col items-center justify-center p-8 bg-slate-50 border-b border-border-base">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-3">
              <Key size={24} className="text-primary" />
            </div>
            <h3 className="text-base font-semibold text-text-base mb-1">Connect your API key</h3>
            <p className="text-sm text-slate-500 mb-4 text-center max-w-sm">
              Enter your client API key to start chatting with agents.
            </p>
            <div className="flex gap-2 w-full max-w-sm">
              <input
                type="password"
                className="input-field flex-1 text-sm"
                placeholder="sk-..."
                value={token}
                onChange={(e) => setTokenState(e.target.value)}
                onKeyDown={handleTokenInputKeyDown}
              />
              <button onClick={handleSaveToken} className="btn btn-primary text-sm">
                Connect
              </button>
            </div>
          </div>
        )}

        {/* Error banner */}
        {runError && (
          <div className="flex items-center gap-2 px-4 py-2 bg-red-50 border-b border-red-100 text-sm text-red-600">
            <AlertCircle size={16} className="shrink-0" />
            <span className="flex-1 truncate">{runError}</span>
            <button onClick={() => setRunError(null)} className="text-red-400 hover:text-red-600 shrink-0">
              Dismiss
            </button>
          </div>
        )}

        {/* Messages */}
        <MessageList
          messages={messages}
          streamingContent={streamingContent}
          streamActivity={streamActivity}
          isStreaming={isStreaming}
        />

        {/* Composer */}
        <Composer
          onSend={handleSend}
          disabled={isStreaming || !tokenSaved}
          onCancel={isStreaming ? handleCancelRun : undefined}
          placeholder={
            !tokenSaved
              ? 'Configure your API token first...'
              : !selectedAgent
                ? 'Select an agent above to start...'
                : 'Type your message...'
          }
        />
      </div>
    </div>
  );
}
