import React, { useState } from 'react';

interface TerminalPanelProps {
  token: string | null;
}

const TerminalPanel: React.FC<TerminalPanelProps> = ({ token }) => {
  const [history, setHistory] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const [isRunning, setIsRunning] = useState(false);

  const runCommand = async () => {
    if (!token) {
      setHistory(prev => [...prev, { type: 'stderr', content: 'Informe uma API key de cliente antes de usar o terminal.' }]);
      return;
    }
    if (!input.trim() || isRunning) return;
    const cmd = input;
    setInput('');
    setIsRunning(true);
    setHistory(prev => [...prev, { type: 'input', content: `$ ${cmd}` }]);

    try {
      const res = await fetch('/v1/ide/run', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ command: cmd })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || `Falha HTTP ${res.status}`);
      }
      if (data.stdout) setHistory(prev => [...prev, { type: 'stdout', content: data.stdout }]);
      if (data.stderr) setHistory(prev => [...prev, { type: 'stderr', content: data.stderr }]);
    } catch (err: any) {
      setHistory(prev => [...prev, { type: 'stderr', content: err?.message || 'Falha ao executar comando.' }]);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-black font-mono text-sm">
      <div className="p-2 bg-gray-800 text-xs font-bold text-gray-400">RESTRICTED TERMINAL</div>
      <div className="flex-1 overflow-y-auto p-2">
        {history.map((h, i) => (
          <div key={i} className={h.type === 'stderr' ? 'text-red-500' : h.type === 'input' ? 'text-blue-400' : 'text-green-400'}>
            <pre className="whitespace-pre-wrap">{h.content}</pre>
          </div>
        ))}
      </div>
      <div className="p-2 border-t border-gray-800 flex gap-2">
        <span className="text-blue-400">$</span>
        <input
          className="flex-1 bg-transparent focus:outline-none text-white disabled:text-gray-600"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && runCommand()}
          disabled={!token || isRunning}
          placeholder={token ? 'ls, cat, pytest...' : 'Informe uma API key de cliente'}
        />
      </div>
    </div>
  );
};

export default TerminalPanel;
