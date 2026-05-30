import { useState, useEffect, useRef } from 'react';
import { Send, Settings, Save, X, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const DEFAULT_AGENT_ID = '85f5dd4f-582d-4ced-a034-0a8a8b043199';
const ADMIN_TOKEN = '917b7930cac1eeabff1496a0604249e9216cd8e15281b97657e155593b219f69';

export const ChatPlayground = () => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your real-time agent. How can I assist you today?' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const connectWebSocket = (runId: string) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = 'localhost:18080'; // Using the exposed port from docker ps
    const ws = new WebSocket(`${protocol}//${host}/v1/agents/runs/${runId}/stream?token=${ADMIN_TOKEN}`);

    ws.onopen = () => {
      console.log('WebSocket Connected');
      toast.success('Streaming connection established');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.event_type === 'step_completed') {
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: `[Step ${data.payload.step_number}] ${data.payload.step_type}: ${data.payload.status}` 
        }]);
      } else if (data.event_type === 'run_completed') {
        setIsLoading(false);
        toast.info('Agent run completed');
        ws.close();
      } else if (data.event_type === 'run_failed') {
        setIsLoading(false);
        toast.error(`Run failed: ${data.payload.error}`);
        ws.close();
      }
    };

    ws.onclose = () => {
      console.log('WebSocket Disconnected');
    };

    wsRef.current = ws;
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    
    const userMessage = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`http://localhost:18080/agents/${DEFAULT_AGENT_ID}/runs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Token': ADMIN_TOKEN
        },
        body: JSON.stringify({
          tenant_id: 'default',
          input_text: userMessage
        })
      });

      if (!response.ok) {
        throw new Error('Failed to initiate agent run');
      }

      const run = await response.json();
      setCurrentRunId(run.id);
      connectWebSocket(run.id);
      
    } catch (error: any) {
      toast.error(error.message);
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] md:h-[calc(100vh-10rem)]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Chat Playground</h1>
        <div className="flex gap-2">
          <button 
            className="btn btn-outline lg:hidden"
            onClick={() => setIsSettingsOpen(!isSettingsOpen)}
          >
            <Settings size={18} />
            {isSettingsOpen ? 'Close Settings' : 'Settings'}
          </button>
          <button className="btn btn-primary sm:w-auto flex-1 sm:flex-none">
            <Save size={18} /> Export
          </button>
        </div>
      </div>

      <div className="flex gap-6 flex-1 min-h-0 relative">
        {/* Chat Main */}
        <div className="flex-1 flex flex-col bg-white border border-border-base rounded-2xl shadow-sm overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4" ref={scrollRef}>
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`
                  max-w-[85%] md:max-w-[70%] p-3 md:p-4 rounded-2xl
                  ${m.role === 'user' 
                    ? 'bg-primary text-white rounded-tr-none' 
                    : 'bg-slate-100 text-slate-900 rounded-tl-none'}
                `}>
                  <p className="text-sm md:text-base leading-relaxed whitespace-pre-wrap">{m.content}</p>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-100 text-slate-500 p-3 rounded-2xl rounded-tl-none flex items-center gap-2">
                  <Loader2 size={16} className="animate-spin" />
                  <span className="text-sm">Agent is thinking...</span>
                </div>
              </div>
            )}
          </div>
          
          <div className="p-4 border-t border-border-base bg-white">
            <div className="flex gap-2 max-w-4xl mx-auto">
              <input 
                type="text" 
                className="input-field rounded-full px-5 py-3" 
                placeholder="Message..." 
                value={input}
                disabled={isLoading}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              />
              <button 
                className={`p-3 rounded-full transition-colors shadow-lg shadow-primary/20 shrink-0 ${isLoading ? 'bg-slate-300 cursor-not-allowed' : 'bg-primary text-white hover:bg-primary/90'}`}
                onClick={handleSend}
                disabled={isLoading}
              >
                {isLoading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
              </button>
            </div>
          </div>
        </div>
        
        {/* Sidebar Settings */}
        <div className={`
          absolute inset-y-0 right-0 z-20 lg:static
          w-full sm:w-80 lg:w-72 bg-white lg:bg-transparent
          transform transition-transform duration-300 lg:transform-none
          ${isSettingsOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'}
          border lg:border-none border-border-base lg:shadow-none shadow-2xl rounded-l-2xl lg:rounded-none
        `}>
          <div className="p-6 h-full overflow-y-auto lg:p-0">
            <div className="flex items-center justify-between mb-6 lg:hidden">
              <h3 className="text-lg font-bold">Parameters</h3>
              <button onClick={() => setIsSettingsOpen(false)} className="p-2 hover:bg-slate-100 rounded-lg">
                <X size={20} />
              </button>
            </div>

            <div className="space-y-6">
              <div className="bg-white p-4 rounded-xl border border-border-base">
                <h4 className="text-sm font-semibold mb-3">Model Selection</h4>
                <select className="input-field py-2 text-sm">
                  <option value="gpt-4">GPT-4 Turbo (default)</option>
                  <option value="gpt-3.5">GPT-3.5 Turbo</option>
                  <option value="claude-3">Claude 3 Opus</option>
                </select>
              </div>

              <div className="bg-white p-4 rounded-xl border border-border-base">
                <div className="flex justify-between mb-2">
                  <h4 className="text-sm font-semibold">Temperature</h4>
                  <span className="text-xs font-mono bg-slate-100 px-1.5 py-0.5 rounded">0.7</span>
                </div>
                <input type="range" className="w-full accent-primary" min="0" max="1" step="0.1" defaultValue="0.7" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
