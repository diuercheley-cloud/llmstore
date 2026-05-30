import React, { useState } from 'react';

const TerminalPanel: React.FC = () => {
  const [history, setHistory] = useState<any[]>([]);
  const [input, setInput] = useState('');

  const runCommand = () => {
    if (!input.trim()) return;
    const cmd = input;
    setInput('');
    setHistory(prev => [...prev, { type: 'input', content: `$ ${cmd}` }]);

    fetch('/v1/ide/run', {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ command: cmd })
    })
      .then(res => res.json())
      .then(data => {
        if (data.stdout) setHistory(prev => [...prev, { type: 'stdout', content: data.stdout }]);
        if (data.stderr) setHistory(prev => [...prev, { type: 'stderr', content: data.stderr }]);
      });
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
          className="flex-1 bg-transparent focus:outline-none text-white"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && runCommand()}
        />
      </div>
    </div>
  );
};

export default TerminalPanel;
