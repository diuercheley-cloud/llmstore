import React, { useState, useEffect } from 'react';

interface AgentMentionPickerProps {
  onSelect: (agent: any) => void;
  filter: string;
}

const AgentMentionPicker: React.FC<AgentMentionPickerProps> = ({ onSelect, filter }) => {
  const [agents, setAgents] = useState<any[]>([]);

  useEffect(() => {
    // In a real app, we'd fetch agents from the API
    setAgents([
      { id: 'agent-1-uuid', name: 'Suporte' },
      { id: 'agent-2-uuid', name: 'Analista' },
    ]);
  }, []);

  const filtered = agents.filter(a => a.name.toLowerCase().includes(filter.toLowerCase()));

  if (filtered.length === 0) return null;

  return (
    <div className="absolute bottom-full left-0 mb-2 w-64 bg-white border rounded shadow-lg overflow-hidden z-50">
      <div className="p-2 bg-gray-50 text-xs font-bold text-gray-500 uppercase">Mencionar Agente</div>
      {filtered.map(agent => (
        <button
          key={agent.id}
          className="w-full text-left px-4 py-2 hover:bg-blue-50 transition"
          onClick={() => onSelect(agent)}
        >
          <div className="font-medium">@{agent.name}</div>
        </button>
      ))}
    </div>
  );
};

export default AgentMentionPicker;
