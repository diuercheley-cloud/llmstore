import { useState } from 'react';
import { Send, Settings, Save, ChevronRight } from 'lucide-react';

export const ChatPlayground = () => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! How can I assist you today?' }
  ]);
  const [input, setInput] = useState('');
  const [model, setModel] = useState('gpt-4');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(1024);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const handleSend = () => {
    if (!input.trim()) return;
    setMessages([...messages, { role: 'user', content: input }]);
    setInput('');
    setTimeout(() => {
      setMessages(prev => [...prev, { role: 'assistant', content: 'This is a simulated response based on the playground settings.' }]);
    }, 1000);
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
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`
                  max-w-[85%] md:max-w-[70%] p-3 md:p-4 rounded-2xl
                  ${m.role === 'user' 
                    ? 'bg-primary text-white rounded-tr-none' 
                    : 'bg-slate-100 text-slate-900 rounded-tl-none'}
                `}>
                  <p className="text-sm md:text-base leading-relaxed">{m.content}</p>
                </div>
              </div>
            ))}
          </div>
          
          <div className="p-4 border-t border-border-base bg-white">
            <div className="flex gap-2 max-w-4xl mx-auto">
              <input 
                type="text" 
                className="input-field rounded-full px-5 py-3" 
                placeholder="Message..." 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              />
              <button 
                className="bg-primary text-white p-3 rounded-full hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20 shrink-0"
                onClick={handleSend}
              >
                <Send size={20} />
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
              <button onClick={() => setIsSettingsOpen(false)} className="p-2 hover:bg-slate-100 rounded-full">
                <ChevronRight size={24} />
              </button>
            </div>
            
            <div className="card space-y-6">
              <div className="hidden lg:flex items-center gap-2 mb-2">
                <Settings size={18} className="text-slate-400" />
                <h3 className="font-bold">Parameters</h3>
              </div>
              
              <div className="space-y-2">
                <label className="text-sm font-semibold text-slate-700">Model</label>
                <select className="input-field cursor-pointer" value={model} onChange={(e) => setModel(e.target.value)}>
                  <option value="gpt-4">GPT-4 Turbo</option>
                  <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                  <option value="claude-3-opus">Claude 3 Opus</option>
                </select>
              </div>

              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <label className="text-sm font-semibold text-slate-700">Temperature</label>
                  <span className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded text-primary">{temperature}</span>
                </div>
                <input 
                  type="range" min="0" max="2" step="0.1" 
                  className="w-full accent-primary h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                  value={temperature} 
                  onChange={(e) => setTemperature(parseFloat(e.target.value))} 
                />
                <div className="flex justify-between text-[10px] text-slate-400 font-medium">
                  <span>PRECISE</span>
                  <span>CREATIVE</span>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-slate-700">Max Tokens</label>
                <input 
                  type="number" className="input-field" 
                  value={maxTokens} 
                  onChange={(e) => setMaxTokens(parseInt(e.target.value))} 
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
